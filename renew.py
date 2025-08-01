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

            # 等待跳转到 dashboard 页面
            print("⏳ 正在等待跳转 dashboard...")
            page.wait_for_url("**/dashboard", timeout=15000)

            print("🎯 登录成功，跳转到续期页面...")
            page.goto(RENEW_URL, timeout=15000)

            # 截图验证是否加载成功
            page.screenshot(path="renew_page.png", full_page=True)
            print("📸 已截图保存 renew_page.png")

            # 检查是否有 Renew 按钮
            if page.locator("text=Renew").first.is_visible():
                print("🔁 找到 Renew 按钮，点击...")
                page.click("text=Renew")
                print("✅ 已点击 Renew 按钮")

                # 等待一小段时间看是否弹出验证
                time.sleep(5)

                # Turnstile 验证（如果存在）
                if page.frame_locator('iframe[title*="Cloudflare"]'):
                    print("⚠️ 检测到 Cloudflare Turnstile 验证，等待用户通过或自动通过...")
                    page.wait_for_selector("iframe[title*='Cloudflare']", timeout=20000)

                    # 可加入额外识别处理逻辑

                time.sleep(5)
                page.screenshot(path="after_renew.png", full_page=True)
                print("✅ 续期操作完成，截图已保存 after_renew.png")
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