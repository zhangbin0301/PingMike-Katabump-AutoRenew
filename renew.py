from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import time

EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"

def safe_screenshot(page, filename: str):
    try:
        page.screenshot(path=filename, full_page=True)
        print(f"📸 已保存截图: {filename}")
    except Exception as e:
        print(f"⚠️ 截图失败 {filename}: {e}")

def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
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
            print("⏳ 等待跳转到 Dashboard...")
            page.wait_for_url("**/dashboard", timeout=20000)

            # 打开续期页面
            print("🎯 打开服务器编辑页面...")
            page.goto(RENEW_URL, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            safe_screenshot(page, "before_renew.png")

            # 点击 Renew 按钮
            print("🟦 点击页面上的第一个 Renew 按钮...")
            renew_btn = page.locator("//button[contains(text(), 'Renew')]").first
            renew_btn.scroll_into_view_if_needed()
            renew_btn.click()

            # 等待弹窗出现
            print("🪟 等待 Renew 弹窗出现...")
            page.wait_for_selector("#renew-modal.show", timeout=10000)

            # 验证码点击
            print("🔍 查找并点击验证码 checkbox...")
            turnstile_iframe = page.frame_locator("#renew-modal iframe[title*='Cloudflare']")
            checkbox = turnstile_iframe.locator("input[type='checkbox']")
            checkbox.wait_for(timeout=10000)
            checkbox.click()
            print("✅ 已点击验证码复选框，等待验证通过...")

            # 等待打勾成功
            turnstile_iframe.locator(".ctp-checkbox-label span.ctp-icon-checkmark").wait_for(timeout=15000)
            print("✅ 验证成功 ✅")
            turnstile_iframe.locator("body").screenshot(path="captcha_frame.png")
            print("📸 已截图验证码 iframe")

            # 点击弹窗中的 Renew 提交按钮
            print("🚀 点击弹窗中的 Renew 提交按钮...")
            modal_renew_btn = page.locator("#renew-modal button.btn-primary[type='submit']")
            modal_renew_btn.wait_for(state="visible", timeout=10000)
            modal_renew_btn.click()

            # 等待续期成功提示
            print("🕵️ 检查是否续期成功...")
            success_alert = page.locator("div.alert-success")
            success_alert.wait_for(timeout=10000)
            print(f"🎉 续期成功: {success_alert.inner_text()}")

            safe_screenshot(page, "after_renew.png")

        except PlaywrightTimeoutError as e:
            print(f"❌ 超时错误: {e}")
            safe_screenshot(page, "timeout_error.png")
        except Exception as e:
            print(f"❌ 异常发生: {e}")
            safe_screenshot(page, "error.png")
        finally:
            print("🚪 关闭浏览器...")
            context.close()
            browser.close()

if __name__ == "__main__":
    main()