from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"

def main():
    print("✅ Starting renewal task...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 调试时可设为 False
        context = browser.new_context()
        page = context.new_page()

        try:
            # 登录流程
            print("🔐 Navigating to login page...")
            page.goto("https://dashboard.katabump.com/login", timeout=20000)
            
            print("🧾 Filling credentials...")
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            
            print("⏳ Waiting for dashboard...")
            page.wait_for_url("**/dashboard", timeout=15000)

            # 续期流程
            print("🎯 Navigating to server page...")
            page.goto(RENEW_URL, timeout=15000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path="before_renew.png")

            # 点击触发模态框的按钮
            print("🔍 Finding renew trigger button...")
            trigger_button = page.wait_for_selector(
                "//td[contains(text(), 'Delete server')]/following-sibling::td//button[contains(text(), 'Renew')]",
                timeout=20000,
                state="visible"
            )
            trigger_button.scroll_into_view_if_needed()
            trigger_button.click()
            
            # 处理模态框
            print("🪟 Waiting for renew modal...")
            page.wait_for_selector("h5.modal-title:has-text('Renew')", timeout=10000)
            
            # 处理Cloudflare验证码
            try:
                if page.query_selector("div.cf-turnstile"):
                    print("🛡️ Handling Cloudflare Turnstile...")
                    turnstile_iframe = page.wait_for_selector(
                        "#renew-modal iframe[title*='Cloudflare']", 
                        timeout=10000
                    )
                    frame = turnstile_iframe.content_frame()
                    checkbox = frame.wait_for_selector("input[type='checkbox']", timeout=5000)
                    checkbox.click()
                    print("✅ Cloudflare checkbox clicked")
                    time.sleep(2)  # 等待验证完成
            except Exception as e:
                print(f"⚠️ Cloudflare handling skipped: {e}")

            # 提交续期
            print("🔵 Clicking final renew button...")
            modal_button = page.wait_for_selector(
                "#renew-modal button.btn-primary[type='submit']", 
                timeout=10000,
                state="visible"
            )
            modal_button.click()
            
            # 验证结果
            print("⏳ Waiting for renewal confirmation...")
            try:
                page.wait_for_selector("div.alert-success", timeout=5000)
                print("🎉 Renewal successful!")
            except:
                print("⚠️ No success message detected (may still have worked)")

            page.screenshot(path="after_renew.png")
            print("✅ Screenshot saved: after_renew.png")

        except PlaywrightTimeoutError as e:
            print(f"❌ Timeout error: {e}")
            page.screenshot(path="timeout_error.png")
        except Exception as e:
            print(f"❌ Error occurred: {e}")
            page.screenshot(path="error.png")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()