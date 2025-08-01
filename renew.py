import os
from playwright.sync_api import sync_playwright
import time

KATABUMP_EMAIL = os.getenv("KATABUMP_EMAIL")
KATABUMP_PASSWORD = os.getenv("KATABUMP_PASSWORD")
SERVER_EDIT_URL = "https://dashboard.katabump.com/servers/edit?id=105562"
TURNSTILE_SITEKEY = "0x4AAAAAAA1IssKDXD0TRMjP"

def main():
    if not KATABUMP_EMAIL or not KATABUMP_PASSWORD:
        print("❌ 错误：请设置 KATABUMP_EMAIL 和 KATABUMP_PASSWORD 环境变量。")
        return

    print("🚀 开始续期任务...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Step 1: 登录 Katabump
            login_url = "https://dashboard.katabump.com/auth/login"
            print(f"🔐 正在打开登录页面: {login_url}")
            page.goto(login_url, wait_until="domcontentloaded", timeout=60000)

            print("📝 输入账号密码并登录...")
            page.fill('input[name="username"]', KATABUMP_EMAIL)
            page.fill('input[name="password"]', KATABUMP_PASSWORD)
            page.click('button[type="submit"]')

            # 等待跳转
            page.wait_for_url("**/servers", timeout=15000)
            print("✅ 登录成功")

            # Step 2: 跳转到服务器编辑页面
            print(f"🌐 打开续期页面: {SERVER_EDIT_URL}")
            page.goto(SERVER_EDIT_URL, wait_until="domcontentloaded", timeout=60000)

            # Step 3: 点击 Renew 按钮（主页面）
            print("🔁 点击 Renew 按钮...")
            page.click('button:has-text("Renew")')

            # Step 4: 等待弹窗加载 + Turnstile 验证框出现
            print("⏳ 等待 Turnstile 验证框加载...")
            page.wait_for_selector('.cf-turnstile', timeout=30000)
            print("✅ Turnstile 加载完成，等待用户手动验证或自动跳过...")

            # 最多等待 90 秒用于验证完成（通常 Cloudflare 自动跳过验证）
            max_wait_time = 90
            for i in range(max_wait_time):
                if page.locator("#cf-chl-widget-*").evaluate_all("els => els.some(el => el.value.length > 10)"):
                    break
                time.sleep(1)

            # Step 5: 点击弹窗内的最终 Renew 提交按钮
            print("🖱️ 点击弹窗中的 Renew 提交按钮...")
            page.click('#renew-modal button.btn-primary[type="submit"]', timeout=10000)

            print("🎉 续期请求已提交，请前往网站确认结果。")

            # 保存截图
            page.screenshot(path="renew_success.png")
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            page.screenshot(path="renew_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    main()