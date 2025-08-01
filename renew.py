from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"

def handle_cloudflare_turnstile(page):
    """专门处理续期模态框内的Cloudflare验证"""
    print("🛡️ 定位续期模态框内的Cloudflare验证...")
    try:
        # 更精确的定位：只在续期模态框内查找
        renew_modal = page.locator("#renew-modal")
        turnstile = renew_modal.locator("div.cf-turnstile")
        
        if turnstile.count() > 0:
            print(f"⚠️ 发现 {turnstile.count()} 个验证组件，精确处理续期模态框内的...")
            turnstile_iframe = renew_modal.locator("iframe[title*='Cloudflare']")
            
            if turnstile_iframe.count() > 0:
                print("✅ 定位到验证iframe，准备点击...")
                frame = turnstile_iframe.first.content_frame()
                checkbox = frame.locator("input[type='checkbox']")
                checkbox.click()
                print("✅ 已点击验证复选框")
                time.sleep(3)  # 等待验证完成
                return True
        return False
    except Exception as e:
        print(f"⚠️ 验证码处理异常: {e}")
        return False

def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 调试时建议可视化
        context = browser.new_context()
        page = context.new_page()

        try:
            # 登录流程
            print("🔐 打开登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=20000)
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url("**/dashboard", timeout=15000)

            # 续期流程
            print("🎯 进入续期页面...")
            page.goto(RENEW_URL, timeout=15000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path="1_before_renew.png")

            # 点击触发按钮
            print("🔍 定位Renew触发按钮...")
            trigger_button = page.locator(
                "//td[contains(text(), 'Delete server')]/following-sibling::td//button[contains(text(), 'Renew')]"
            ).first
            trigger_button.scroll_into_view_if_needed()
            trigger_button.click()
            
            # 等待模态框
            print("🪟 等待续期弹窗...")
            page.wait_for_selector("#renew-modal h5.modal-title:has-text('Renew')", timeout=10000)
            page.screenshot(path="2_modal_opened.png")

            # 处理验证码
            if handle_cloudflare_turnstile(page):
                print("✅ 验证码处理完成")
            else:
                print("⏩ 未检测到需要处理的验证码")

            # 提交续期
            print("🚀 提交续期请求...")
            submit_button = page.locator("#renew-modal button.btn-primary[type='submit']").first
            submit_button.click()
            
            # 验证结果
            try:
                page.wait_for_selector("div.alert-success", timeout=5000)
                print("🎉 续期成功！")
            except:
                print("⚠️ 未检测到成功提示（可能仍需手动确认）")

            page.screenshot(path="3_after_renew.png")

        except Exception as e:
            print(f"❌ 发生错误: {e}")
            page.screenshot(path="error.png")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()