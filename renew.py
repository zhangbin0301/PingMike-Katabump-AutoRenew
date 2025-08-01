from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"

def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("🔐 打开登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=20000)

            print("🧾 输入账号密码...")
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')

            print("⏳ 正在等待跳转 dashboard...")
            page.wait_for_url("**/dashboard", timeout=15000)

            print("🎯 登录成功，跳转到续期页面...")
            page.goto(RENEW_URL, timeout=15000)

            print("🔁 寻找并点击第一个蓝色 Renew 按钮...")
            renew_button = page.wait_for_selector("button.btn-primary:has-text('Renew')", timeout=10000)
            renew_button.click()

            print("⏳ 等待弹窗加载中...")
            page.wait_for_selector("div.modal-body form", timeout=10000)
            print("📦 弹窗已加载，准备处理 Turnstile 验证...")

            # 检查 Turnstile iframe
            try:
                turnstile_iframe = page.wait_for_selector("#renew-modal iframe[title*='Cloudflare']", timeout=10000)
                if turnstile_iframe:
                    print("⚠️ 检测到 Turnstile 验证，尝试点击勾选...")

                    frame = turnstile_iframe.content_frame()
                    if frame:
                        checkbox = frame.wait_for_selector('input[type="checkbox"]', timeout=5000)
                        checkbox.click()
                        print("✅ 已点击 Turnstile 勾选框")

                        # 等待验证通过（iframe 消失）
                        page.wait_for_selector("#renew-modal iframe[title*='Cloudflare']", state="detached", timeout=30000)
                        print("✅ Turnstile 验证已通过")
                    else:
                        print("⚠️ 无法获取 iframe 内部 frame")
                else:
                    print("⏩ 未检测到 Turnstile 验证，可能已跳过")

            except PlaywrightTimeoutError as e:
                print(f"⚠️ Turnstile 验证 iframe 加载失败: {e}")

            # 提交续期
            print("🚀 点击弹窗内最终 Renew 提交按钮...")
            page.click('#renew-modal button[type="submit"].btn-primary', timeout=5000)

            # 等待一下执行效果
            time.sleep(2)
            page.screenshot(path="after_renew.png", full_page=True)
            print("✅ 续期完成，截图已保存 after_renew.png")

        except PlaywrightTimeoutError as e:
            print(f"❌ 页面超时: {e}")
            page.screenshot(path="timeout_error.png", full_page=True)
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            page.screenshot(path="general_error.png", full_page=True)
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()