import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def add_server_time(server_url="https://dashboard.katabump.com/servers/edit?id=105562"):
    katabump_cookie_raw = os.environ.get('KATABUMP_COOKIE')
    katabump_email = os.environ.get('KATABUMP_EMAIL')
    katabump_password = os.environ.get('KATABUMP_PASSWORD')

    if not (katabump_cookie_raw or (katabump_email and katabump_password)):
        print("错误: 未提供 Cookie 或账号密码。")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(90000)

        try:
            login_success = False

            # ----- 尝试 Cookie 登录 -----
            if katabump_cookie_raw:
                print("正在尝试使用 Cookie 登录...")

                # 转换 cookie 字符串为列表
                cookies = []
                for part in katabump_cookie_raw.split(';'):
                    if '=' in part:
                        name, value = part.strip().split('=', 1)
                        cookies.append({
                            "name": name,
                            "value": value,
                            "domain": "dashboard.katabump.com",
                            "path": "/",
                            "httpOnly": False,
                            "secure": True
                        })

                context.add_cookies(cookies)
                page.goto(server_url, wait_until="domcontentloaded")

                if "login" not in page.url:
                    print("✅ Cookie 登录成功")
                    login_success = True
                else:
                    print("⚠️ Cookie 登录失败，准备切换为账号密码登录。")
                    page.screenshot(path="cookie_login_failed.png")

            # ----- 如果 Cookie 失败，就尝试账号密码登录 -----
            if not login_success:
                if not (katabump_email and katabump_password):
                    print("错误: Cookie 无效，且未提供账号密码。")
                    browser.close()
                    return False

                login_url = "https://dashboard.katabump.com/auth/login"
                print(f"访问登录页面: {login_url}")
                page.goto(login_url, wait_until="domcontentloaded")

                page.wait_for_selector('input[name="username"]')
                page.wait_for_selector('input[name="password"]')
                page.wait_for_selector('button[type="submit"]')

                print("填写账号密码并提交...")
                page.fill('input[name="username"]', katabump_email)
                page.fill('input[name="password"]', katabump_password)

                with page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
                    page.click('button[type="submit"]')

                if "login" in page.url or "auth" in page.url:
                    print("❌ 登录失败")
                    page.screenshot(path="login_failed.png")
                    browser.close()
                    return False
                else:
                    print("✅ 账号密码登录成功")
                    login_success = True

            # ----- 导航到目标服务器页面 -----
            print("进入服务器页面...")
            page.goto(server_url, wait_until="domcontentloaded")

            # 点击 Renew 按钮，等待弹窗
            print("查找 Renew 按钮...")
            page.click('text=Renew')
            page.wait_for_selector('#renew-modal.show', timeout=10000)

            # 等待 Turnstile 验证通过
            print("等待 Cloudflare Turnstile 验证（如果有）...")
            page.wait_for_function("""
                () => {
                    const el = document.querySelector('input[name="cf-turnstile-response"]');
                    return el && el.value && el.value.length > 10;
                }
            """, timeout=15000)

            print("点击弹窗中的 Renew 提交按钮...")
            page.click('#renew-modal button[type="submit"]')

            time.sleep(5)
            print("✅ 续期成功")
            browser.close()
            return True

        except Exception as e:
            print(f"发生错误: {e}")
            try:
                page.screenshot(path="general_error.png", full_page=True)
                print("⚠️ 已保存页面截图 general_error.png")
            except:
                print("截图失败")
            browser.close()
            return False

if __name__ == "__main__":
    print("开始执行续期任务...")
    success = add_server_time()
    exit(0 if success else 1)