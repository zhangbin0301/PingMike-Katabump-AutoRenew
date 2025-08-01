from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

# 从环境变量读取敏感信息是一种好习惯
EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"

def click_turnstile_checkbox(page):
    """
    处理 Cloudflare Turnstile 验证码。
    """
    max_retry = 3
    for attempt in range(max_retry):
        try:
            print(f"尝试获取 Turnstile iframe（第 {attempt+1} 次）...")
            # 等待 iframe 出现
            iframe_el = page.wait_for_selector("#renew-modal iframe[title*='Cloudflare']", timeout=15000)
            frame = iframe_el.content_frame()
            if not frame:
                raise Exception("未能获取 iframe 内部 frame")

            print("等待勾选框出现并点击...")
            checkbox = frame.wait_for_selector('input[type="checkbox"]', timeout=10000)
            checkbox.click()

            print("等待 Turnstile 验证通过...")
            # 验证成功后，通常 iframe 会消失或者其内容会改变
            # 等待 iframe 分离 (detached) 是一个可靠的信号
            page.wait_for_selector("#renew-modal iframe[title*='Cloudflare']", state="detached", timeout=30000)
            print("✅ Turnstile 验证通过")
            return True
        except Exception as e:
            print(f"⚠️ Turnstile 勾选尝试失败: {e}")
            if attempt < max_retry - 1:
                print("重试中...")
                page.screenshot(path=f"turnstile_retry_fail_{attempt+1}.png")
                time.sleep(3)
            else:
                print("❌ 超过最大重试次数，放弃")
                page.screenshot(path=f"turnstile_max_fail_attempt_{attempt+1}.png")
                return False

def main():
    print("✅ 开始执行续期任务...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # 建议在调试时设置为 False，方便观察
        context = browser.new_context()
        page = context.new_page()

        try:
            print("🔐 打开登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=30000)

            print("🧾 输入账号密码...")
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')

            print("⏳ 正在等待跳转 dashboard...")
            page.wait_for_url("**/dashboard", timeout=20000)

            print("🎯 登录成功，跳转到续期页面...")
            page.goto(RENEW_URL, timeout=20000)

            renew_button_selector = 'button:has-text("Renew")'
            
            # 等待第一个 Renew 按钮出现
            print("🔍 正在查找 Renew 按钮...")
            page.wait_for_selector(renew_button_selector, state="visible", timeout=10000)
            
            # 点击按钮以打开弹窗
            print("🔁 找到 Renew 按钮，点击打开弹窗...")
            page.locator(renew_button_selector).first.click()

            # --- 关键修改 ---
            # 放弃使用 time.sleep()，直接等待弹窗变得可见
            print("⏳ 等待续期弹窗加载并显示...")
            try:
                page.wait_for_selector("#renew-modal", state="visible", timeout=15000)
                print("✅ 弹窗已显示，开始处理 Turnstile 验证码")
                page.screenshot(path="renew_modal_visible.png", full_page=True)

                if click_turnstile_checkbox(page):
                    print("🚀 点击弹窗内最终的 Renew 提交按钮...")
                    # 使用更明确的选择器来点击弹窗内的提交按钮
                    page.locator('#renew-modal form button[type="submit"]').click()
                    
                    # 等待一下，让续期请求有时间完成，可以观察网络活动或等待某个成功提示
                    print("⏳ 等待续期操作完成...")
                    # 例如，可以等待页面刷新或出现成功提示
                    page.wait_for_load_state('networkidle', timeout=10000)
                    
                    print("🎉 续期成功!")
                    page.screenshot(path="after_renew_success.png", full_page=True)
                else:
                    print("❌ Turnstile 验证失败，续期未完成")

            except PlaywrightTimeoutError:
                print("❌ 等待续期弹窗超时，未能显示弹窗。")
                page.screenshot(path="renew_modal_timeout.png", full_page=True)

        except PlaywrightTimeoutError as e:
            print(f"❌ 页面超时: {e}")
            page.screenshot(path="timeout_error.png", full_page=True)
        except Exception as e:
            print(f"❌ 发生未知错误: {e}")
            page.screenshot(path="general_error.png", full_page=True)
        finally:
            print("✅ 任务执行完毕，关闭浏览器。")
            context.close()
            browser.close()

if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        print("❌ 请先设置环境变量 KATABUMP_EMAIL 和 KATABUMP_PASSWORD")
    else:
        main()

