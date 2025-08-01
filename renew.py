import os
import time
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()

    page = context.new_page()

    server_edit_url = "https://dashboard.katabump.com/servers/edit?id=105562"

    # ✅ 尝试使用 cookies 登录
    print("开始续期任务...")
    katabump_cookie = os.getenv("KATABUMP_COOKIE", "").strip()
    pterodactyl_email = os.getenv("KATABUMP_EMAIL", "").strip()
    pterodactyl_password = os.getenv("KATABUMP_PASSWORD", "").strip()

    if katabump_cookie:
        print("正在尝试使用 Cookie 登录...")
        try:
            cookies = []
            for item in katabump_cookie.split(";"):
                name, value = item.strip().split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".katabump.com",
                    "path": "/"
                })
            context.add_cookies(cookies)
        except Exception as e:
            print(f"❌ Cookie 格式错误: {e}")
            page.screenshot(path="invalid_cookie_format.png")
            browser.close()
            return

    try:
        print("正在打开服务器页面...")
        page.goto(server_edit_url, wait_until="domcontentloaded", timeout=90000)

        # ⚠️ 检测是否跳转到登录页
        if "auth/login" in page.url or "login" in page.url:
            print("⚠️ Cookie 登录无效，尝试账号密码登录...")

            if not pterodactyl_email or not pterodactyl_password:
                print("❌ Cookie 无效，且未提供账号密码，无法登录")
                page.screenshot(path="cookie_invalid_no_password.png")
                browser.close()
                return

            # 执行账号密码登录
            login_url = "https://dashboard.katabump.com/auth/login"
            page.goto(login_url, wait_until="domcontentloaded", timeout=90000)

            page.wait_for_selector('input[name="username"]')
            page.fill('input[name="username"]', pterodactyl_email)
            page.fill('input[name="password"]', pterodactyl_password)
            page.click('button[type="submit"]')

            # 登录后可能跳转
            page.wait_for_load_state("domcontentloaded")
            if "login" in page.url or "auth" in page.url:
                print("❌ 邮箱密码登录失败")
                page.screenshot(path="login_failed.png")
                browser.close()
                return
            print("✅ 邮箱密码登录成功")

        # 成功进入目标页
        print("✅ 成功进入服务器编辑页面，等待 Turnstile 验证出现...")
        page.wait_for_selector('iframe[src*="challenges.cloudflare.com"]', timeout=90000)
        print("🔁 等待用户完成 Cloudflare 验证（手动或自动）...")
        time.sleep(20)  # 如果你有破解机制可替换此等待

        # 检查 Renew 按钮
        renew_selector = "button:text-is('Renew')"
        page.wait_for_selector(renew_selector, timeout=30000)
        page.click(renew_selector)
        print("✅ 点击 Renew 成功")

        time.sleep(5)
        browser.close()

    except Exception as e:
        print(f"发生错误: {e}")
        page.screenshot(path="general_error.png")
        browser.close()
        exit(1)

with sync_playwright() as playwright:
    run(playwright)