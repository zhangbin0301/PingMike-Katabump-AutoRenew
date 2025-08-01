from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

# --- 全局变量 ---
EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"


def handle_cloudflare_turnstile(page):
    """
    处理续期模态框内的 Cloudflare 验证。
    通过定位模态框，再在内部查找 iframe，避免严格模式冲突。
    """
    print("🛡️ 开始处理 Cloudflare 验证码...")
    try:
        renew_modal = page.locator("#renew-modal")
        turnstile_iframe = renew_modal.locator("iframe[title*='Cloudflare']")

        if turnstile_iframe.count() > 0:
            print("✅ 找到验证码 iframe，准备点击...")
            frame = turnstile_iframe.first.content_frame()

            checkbox = frame.locator("input[type='checkbox']")
            checkbox.wait_for(timeout=10000, state="visible")
            checkbox.click()

            print("⏳ 等待验证响应...")
            time.sleep(3)  # 简单延时等待验证完成
            return True
        else:
            print("⏩ 未找到 Cloudflare iframe，跳过处理。")
            return False

    except Exception as e:
        print(f"❌ 验证码处理异常: {e}")
        return False


def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        launch_options = {
            "headless": False,  # 调试时建议 False，生产环境可以改为 True
            "args": ["--no-sandbox"],  # 在服务器或 Docker 中避免权限问题
        }

        browser = p.chromium.launch(**launch_options)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 登录流程
            print("🔐 打开登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=30000)
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url("**/dashboard", timeout=20000)
            print("✅ 登录成功")

            # 进入续期页面
            print("🎯 进入续期页面...")
            page.goto(RENEW_URL, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            page.screenshot(path="1_server_page.png")

            # 点击Renew按钮
            print("🔍 定位并点击 'Renew' 按钮...")
            trigger_button = page.locator("button.btn-primary:has-text('Renew')").first
            trigger_button.scroll_into_view_if_needed()
            trigger_button.click()

            # 等待模态框出现
            print("🪟 等待续期弹窗加载...")
            renew_modal_title = page.locator("#renew-modal h5.modal-title:has-text('Renew')")
            renew_modal_title.wait_for(timeout=15000, state="visible")
            page.screenshot(path="2_modal_opened.png")
            print("✅ 续期弹窗已打开")

            # 处理 Cloudflare 验证
            handle_cloudflare_turnstile(page)

            # 点击提交续期
            print("🚀 点击最终的提交按钮...")
            submit_button = page.locator("#renew-modal button.btn-primary[type='submit']").first
            submit_button.wait_for(timeout=5000, state="enabled")
            submit_button.click()

            # 等待结果提示
            print("⏳ 等待续期结果...")
            try:
                success_alert = page.locator("div.alert-success")
                success_alert.wait_for(timeout=10000)
                print(f"🎉 续期成功！消息: '{success_alert.inner_text()}'")
            except PlaywrightTimeoutError:
                print("⚠️ 未检测到成功提示，请检查截图或手动确认。")

            page.screenshot(path="3_after_submit.png")

        except Exception as e:
            print(f"❌ 任务执行期间发生致命错误: {e}")
            page.screenshot(path="fatal_error.png")

        finally:
            print("🚪 任务结束，关闭浏览器。")
            context.close()
            browser.close()


if __name__ == "__main__":
    main()