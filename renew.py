import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
SERVER_ID = os.getenv("KATABUMP_SERVER_ID")

if not EMAIL or not PASSWORD or not SERVER_ID:
    raise Exception("缺少必要的环境变量: KATABUMP_EMAIL, KATABUMP_PASSWORD, KATABUMP_SERVER_ID")

def save_screenshot(page, name):
    page.screenshot(path=f"{name}.png", full_page=True)
    print(f"📸 已保存截图: {name}.png")

def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("🔐 打开登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=60000)
            page.fill('input[type="email"]', EMAIL)
            page.fill('input[type="password"]', PASSWORD)
            page.click('button:has-text("Login")')

            print("⏳ 等待跳转到 Dashboard...")
            page.wait_for_url("**/dashboard", timeout=30000)

            print("🎯 打开服务器编辑页面...")
            page.goto(f"https://dashboard.katabump.com/servers/edit?id={SERVER_ID}", timeout=30000)
            save_screenshot(page, "before_renew")

            print("🟦 查找 Renew 按钮...")
            renew_buttons = page.locator("button.btn.btn-primary:has-text('Renew')")
            renew_buttons.first.click()

            print("🪟 等待 Renew 弹窗加载...")
            page.wait_for_selector("#renew-modal", state="visible", timeout=10000)

            print("🛡️ 查找验证码 iframe...")
            iframe_element = page.wait_for_selector("#renew-modal iframe[title*='Cloudflare']", timeout=10000)
            iframe = iframe_element.content_frame()

            if iframe is None:
                raise Exception("⚠️ 无法获取验证码 iframe 的内容")

            print("🔍 点击验证码 checkbox...")
            iframe.wait_for_selector('input[type="checkbox"]', timeout=10000)
            iframe.click('input[type="checkbox"]')

            print("⏳ 等待验证码通过...")
            time.sleep(8)

            print("✅ 提交 Renew...")
            page.locator('#renew-modal button.btn.btn-primary:has-text("Renew")').click()

            print("🕵️ 检查是否续期成功...")
            page.wait_for_timeout(3000)
            save_screenshot(page, "after_renew")

        except PlaywrightTimeoutError as e:
            print(f"❌ 超时错误: {e}")
            save_screenshot(page, "timeout_error")
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            save_screenshot(page, "exception")
        finally:
            print("🚪 关闭浏览器...")
            browser.close()

if __name__ == "__main__":
    main()