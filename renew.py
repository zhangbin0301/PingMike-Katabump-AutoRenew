from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os

# --- 环境变量 ---
EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"

# --- 封装全页截图函数 ---
def safe_screenshot(page, filename: str):
    try:
        page.screenshot(path=filename, full_page=True)
        print(f"📸 已保存截图: {filename}")
    except Exception as e:
        print(f"⚠️ 截图失败 {filename}: {e}")

def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        launch_options = {
            "headless": True,
            "args": ["--no-sandbox"]
        }
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. 登录
            print("🔐 打开登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=30000)
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')

            print("⏳ 等待跳转到 Dashboard...")
            page.wait_for_url("**/dashboard", timeout=20000)

            # 2. 访问续期页面
            print("🎯 打开服务器编辑页面...")
            page.goto(RENEW_URL, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            safe_screenshot(page, "before_renew.png")

            # 3. 点击 Renew 按钮
            print("🟦 查找 Renew 按钮...")
            trigger_button = page.locator("//button[contains(text(), 'Renew')]").first
            trigger_button.scroll_into_view_if_needed()
            trigger_button.click()

            print("🪟 等待 Renew 弹窗加载...")
            page.wait_for_selector("h5.modal-title:has-text('Renew')", timeout=15000)

            # 4. 处理 Cloudflare Turnstile 验证
            try:
                print("🛡️ 查找验证码 iframe...")
                turnstile_iframe = page.locator("#renew-modal iframe[title*='Cloudflare']").first
                turnstile_iframe.wait_for(timeout=10000)
                frame = turnstile_iframe.content_frame()

                checkbox = frame.locator("input[type='checkbox']")
                checkbox.wait_for(state="visible", timeout=5000)
                checkbox.click()
                print("☑️ 已点击验证码复选框，等待验证完成...")

                # 等待 ✅ 图标出现
                frame.wait_for_selector(".ctp-checkbox-label span.ctp-icon-checkmark", timeout=10000)
                print("✅ Cloudflare 验证通过！")

                # 独立截图 iframe
                frame.screenshot(path="captcha_frame.png")
                print("📸 已保存验证码截图: captcha_frame.png")

            except PlaywrightTimeoutError:
                print("⏰ 验证码加载或验证超时")
            except Exception as e:
                print(f"⚠️ 验证码处理异常: {e}")

            # 5. 提交续期
            print("🔵 点击 Renew 提交按钮...")
            modal_button = page.locator("#renew-modal button.btn-primary[type='submit']")
            modal_button.wait_for(state="visible", timeout=10000)
            modal_button.click()

            # 6. 检查是否成功
            print("🕵️ 检查是否续期成功...")
            try:
                success_alert = page.locator("div.alert-success")
                success_alert.wait_for(timeout=10000)
                print(f"🎉 续期成功: {success_alert.inner_text()}")
            except PlaywrightTimeoutError:
                print("⚠️ 未检测到成功提示")

            safe_screenshot(page, "after_renew.png")

        except PlaywrightTimeoutError as e:
            print(f"❌ 操作超时: {e}")
            safe_screenshot(page, "timeout_error.png")
        except Exception as e:
            print(f"❌ 脚本执行异常: {e}")
            safe_screenshot(page, "error.png")
        finally:
            print("🚪 关闭浏览器...")
            context.close()
            browser.close()

if __name__ == "__main__":
    main()