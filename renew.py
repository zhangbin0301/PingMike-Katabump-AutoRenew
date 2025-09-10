from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os

EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=128366"

# 插件路径（必须和 yml 里解压一致）
EXT_PATH = os.path.abspath("extensions/captcha-solver")

def safe_screenshot(page, filename: str):
    try:
        page.screenshot(path=filename, full_page=True)
        print(f"📸 已保存截图: {filename}")
    except Exception as e:
        print(f"⚠️ 截图失败 {filename}: {e}")

def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # 插件必须非 headless
            args=[
                "--no-sandbox",
                f"--disable-extensions-except={EXT_PATH}",
                f"--load-extension={EXT_PATH}",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Europe/Berlin",
        )
        page = context.new_page()

        try:
            # 登录
            print("🔐 打开登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=30000)
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            print("⏳ 等待跳转至 Dashboard...")
            page.wait_for_url("**/dashboard", timeout=20000)

            # 打开续期页面
            print("🎯 打开服务器编辑页面...")
            page.goto(RENEW_URL, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            safe_screenshot(page, "00_before_renew.png")

            # 点击 Renew 按钮
            renew_btn = page.locator("//button[contains(text(), 'Renew')]").first
            renew_btn.scroll_into_view_if_needed()
            renew_btn.click()

            # 等待弹窗 & Turnstile iframe
            print("🪟 等待 Renew 弹窗显示...")
            page.wait_for_selector("#renew-modal.show", timeout=15000)

            print("🔍 等待 Turnstile iframe...")
            page.wait_for_function(
                "() => Array.from(document.querySelectorAll('iframe')).some(f => f.src.includes('turnstile'))",
                timeout=30000
            )
            safe_screenshot(page, "01_before_captcha.png")

            # 给扩展一点时间自动处理
            print("🤖 等待扩展自动验证...")
            page.wait_for_timeout(10000)

            # 检查是否验证成功
            page.wait_for_function(
                """() => {
                    const span = document.querySelector('#renew-modal .ctp-icon-checkmark');
                    return span && getComputedStyle(span).display !== 'none';
                }""",
                timeout=30000
            )
            print("✅ 验证成功")
            safe_screenshot(page, "02_captcha_checked.png")

            # 点击 Renew 提交按钮
            modal_renew_btn = page.locator("#renew-modal button.btn-primary[type='submit']")
            modal_renew_btn.wait_for(state="visible", timeout=10000)
            modal_renew_btn.click()

            # 确认续期成功
            success_alert = page.locator("div.alert-success")
            success_alert.wait_for(timeout=10000)
            print(f"🎉 续期成功: {success_alert.inner_text()}")
            safe_screenshot(page, "03_after_renew.png")

        except PlaywrightTimeoutError as e:
            print(f"❌ 超时错误: {e}")
            safe_screenshot(page, "99_timeout_error.png")
        except Exception as e:
            print(f"❌ 异常发生: {e}")
            safe_screenshot(page, "99_exception_error.png")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()