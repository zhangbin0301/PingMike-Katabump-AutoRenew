import os
import time
from playwright.sync_api import sync_playwright

KATABUMP_EMAIL = os.environ["KATABUMP_EMAIL"]
KATABUMP_PASSWORD = os.environ["KATABUMP_PASSWORD"]
KATABUMP_SERVER_ID = os.environ["KATABUMP_SERVER_ID"]

RENEW_URL = f"https://dashboard.katabump.com/servers/edit?id={KATABUMP_SERVER_ID}"
SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def screenshot(page, name):
    path = f"{SCREENSHOT_DIR}/{name}"
    page.screenshot(path=path, full_page=True)
    print(f"📸 已保存截图: {name}")

def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 登录
            print("🔐 正在登录...")
            page.goto("https://dashboard.katabump.com/login", timeout=30000)
            page.fill("input[name='email']", KATABUMP_EMAIL)
            page.fill("input[name='password']", KATABUMP_PASSWORD)
            page.click("button[type='submit']")
            page.wait_for_url("**/dashboard", timeout=30000)

            # 跳转到续期页面
            print("🎯 跳转到续期页面...")
            page.goto(RENEW_URL, timeout=30000)

            # 点击 Renew 按钮弹出弹窗
            print("🟦 查找 Renew 按钮并点击...")
            page.locator("button.btn.btn-primary:has-text('Renew')").nth(0).click()

            # 等待弹窗显示（注意只等 id="renew-modal" 的元素）
            print("🪟 等待 Renew 弹窗显示...")
            page.wait_for_selector("#renew-modal.show", timeout=10000)

            # 等待验证码容器 cf-turnstile 出现
            print("🔍 等待 Turnstile 验证容器出现...")
            page.wait_for_selector("#renew-modal .cf-turnstile", timeout=15000)

            # 等待 iframe 加载到容器中
            print("🧭 等待 iframe 加载进入 DOM...")
            def iframe_present():
                container = page.query_selector("#renew-modal .cf-turnstile")
                if not container:
                    return False
                return container.query_selector("iframe") is not None

            page.wait_for_function(iframe_present, timeout=30000)

            # ✅ 点击 iframe 中的 checkbox
            print("🧩 尝试点击验证框 checkbox...")
            iframe = page.query_selector("#renew-modal .cf-turnstile iframe")
            if iframe:
                frame = iframe.content_frame()
                checkbox = frame.query_selector("input[type='checkbox']")
                if checkbox:
                    checkbox.click()
                    print("☑️ 已点击验证码 checkbox")
                else:
                    print("⚠️ 未找到 checkbox，可能已被替换为图形验证")
            else:
                print("❌ 没有找到 iframe，无法点击验证框")

            # 等待验证成功图标（打勾）
            print("⏳ 等待验证成功图标出现...")
            page.wait_for_function(
                """() => {
                    const span = document.querySelector('.ctp-icon-checkmark');
                    return span && getComputedStyle(span).display !== 'none';
                }""",
                timeout=30000
            )
            print("✅ 验证成功")

            # 点击 Renew 提交按钮
            print("🚀 提交续期...")
            page.click("#renew-modal button.btn.btn-primary:has-text('Renew')")

            # 等待刷新或跳转
            time.sleep(5)
            screenshot(page, "success.png")
            print("✅ 续期成功完成")

        except Exception as e:
            print(f"❌ 发生错误: {e}")
            screenshot(page, "99_timeout_error.png")
        finally:
            print("🚪 关闭浏览器...")
            browser.close()

if __name__ == "__main__":
    main()