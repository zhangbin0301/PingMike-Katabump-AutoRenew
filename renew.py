import os
import time
from playwright.sync_api import sync_playwright, Cookie, TimeoutError as PlaywrightTimeoutError

def add_server_time(server_url="https://dashboard.katabump.com/servers/edit?id=105562"):
    """
    尝试访问 katabump 服务器页面，点击 Renew 按钮并自动等待 Cloudflare 验证。
    支持使用 katabump_s 等 Cookie 登录。
    """
    # 获取 Katabump Cookie 字符串（传入完整字符串）
    katabump_cookie_raw = os.environ.get('KATABUMP_COOKIE')
    if not katabump_cookie_raw:
        print("错误: 未提供 KATABUMP_COOKIE 环境变量。")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(90000)

        try:
            # 解析 cookie 字符串
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

            print("已设置 cookies，正在打开服务器页面...")
            page.goto(server_url, wait_until="domcontentloaded")

            if "login" in page.url or "auth" in page.url:
                print("Cookie 登录失败，仍跳转到了登录页。")
                page.screenshot(path="cookie_login_failed.png")
                browser.close()
                return False

            # 点击 Renew 按钮，弹出 modal
            print("查找 Renew 按钮...")
            page.click('text=Renew')

            # 等待弹窗出现
            print("等待 Renew 弹窗...")
            page.wait_for_selector('#renew-modal.show', timeout=10000)

            # 等待 Cloudflare Turnstile 自动验证完成（最多15秒）
            print("等待 Cloudflare Turnstile 验证...")
            page.wait_for_function("""
                () => {
                    const el = document.querySelector('input[name="cf-turnstile-response"]');
                    return el && el.value && el.value.length > 10;
                }
            """, timeout=15000)

            print("验证成功，点击 Renew 提交按钮...")
            page.click('#renew-modal button[type="submit"]')

            # 等待服务器响应
            time.sleep(5)
            print("续期操作完成。")
            browser.close()
            return True

        except Exception as e:
            print(f"发生错误: {e}")
            page.screenshot(path="exception_error.png")
            browser.close()
            return False

if __name__ == "__main__":
    print("开始续期任务...")
    result = add_server_time()
    exit(0 if result else 1)
