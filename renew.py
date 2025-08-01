from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"

def click_turnstile_checkbox(page):
    max_retry = 3
    for attempt in range(max_retry):
        try:
            print(f"尝试获取 Turnstile iframe（第 {attempt+1} 次）...")
            iframe_el = page.wait_for_selector("#renew-modal iframe[title*='Cloudflare']", timeout=10000)
            frame = iframe_el.content_frame()
            if not frame:
                raise Exception("未能获取 iframe 内部 frame")

            print("等待勾选框出现...")
            checkbox = frame.wait_for_selector('input[type="checkbox"]', timeout=5000)

            print("点击 Turnstile 勾选框...")
            checkbox.click()

            # 等待验证成功的条件（这里用 iframe 消失代替）
            page.wait_for_selector("#renew-modal iframe[title*='Cloudflare']", state="detached", timeout=30000)
            print("✅ Turnstile 验证通过")
            return True
        except Exception as e:
            print(f"⚠️ Turnstile 勾选尝试失败: {e}")
            if attempt < max_retry - 1:
                print("重试中...")
                time.sleep(3)
            else:
                print("❌ 超过最大重试次数，放弃")
                page.screenshot(path=f"turnstile_fail_attempt_{attempt+1}.png")
                return False

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

            page.screenshot(path="renew_page.png", full_page=True)
            print("📸 已截图保存 renew_page.png")

            if page.locator("text=Renew").first.is_visible():
                print("🔁 找到 Renew 按钮，点击打开弹窗...")
                page.click("text=Renew")

                try:
                    # 等待 modal DOM 插入
                    modal = page.wait_for_selector("#renew-modal", state="attached", timeout=10000)
                    print("📦 弹窗 DOM 已加载，截图确认状态...")
                    page.screenshot(path="renew_modal.png", full_page=True)

                    display = modal.evaluate("el => window.getComputedStyle(el).display")
                    print(f"弹窗 display 样式是: {display}")

                    if display == "none":
                        print("⚠️ 弹窗存在但不可见，等待2秒后重试获取显示状态...")
                        time.sleep(2)
                        display = modal.evaluate("el => window.getComputedStyle(el).display")
                        print(f"二次检测弹窗 display 样式是: {display}")

                        if display == "none":
                            print("❌ 弹窗仍不可见，跳过后续操作")
                            return
                        else:
                            print("✅ 弹窗已显示，继续操作")

                    # 自动勾选 Turnstile
                    if click_turnstile_checkbox(page):
                        print("🚀 点击弹窗内最终 Renew 提交按钮...")
                        page.click('#renew-modal button[type="submit"].btn-primary')

                        time.sleep(2)
                        page.screenshot(path="after_renew.png", full_page=True)
                        print("✅ 续期完成，截图已保存 after_renew.png")
                    else:
                        print("❌ Turnstile 验证失败，续期未完成")

                except PlaywrightTimeoutError as e:
                    print(f"❌ 弹窗或验证码处理超时: {e}")
                    page.screenshot(path="modal_timeout.png", full_page=True)

            else:
                print("⚠️ 未找到 Renew 按钮，请检查页面状态")
                page.screenshot(path="no_renew_button.png", full_page=True)

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