from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

# --- 全局变量 ---
EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"


def handle_cloudflare_turnstile(page):
    """
    专门处理续期模态框内的Cloudflare验证。
    通过先定位模态框，再在内部查找，来避免严格模式冲突。
    """
    print("🛡️ 开始处理 Cloudflare 验证码...")
    try:
        # 1. 首先，唯一定位到当前可见的续期模态框
        renew_modal = page.locator("#renew-modal")

        # 2. 在这个模态框内部查找 iframe
        turnstile_iframe = renew_modal.locator("iframe[title*='Cloudflare']")

        # 检查 iframe 是否存在
        if turnstile_iframe.count() > 0:
            print("✅ 找到验证码 iframe，准备点击...")
            # 获取 iframe 的内容 frame
            frame = turnstile_iframe.first.content_frame()
            
            # 在 frame 内部查找并点击复选框
            checkbox = frame.locator("input[type='checkbox']")
            checkbox.wait_for(timeout=10000, state="visible") # 等待复选框可见
            checkbox.click()
            
            # 等待验证完成。等待 iframe 消失或提交按钮可用是更可靠的方式，
            # 但简单的延时在这里通常也有效。
            print("⏳ 等待验证响应...")
            time.sleep(3) 
            return True
        else:
            print("⏩ 在续期弹窗内未找到 Cloudflare iframe，跳过处理。")
            return False
            
    except Exception as e:
        print(f"❌ 验证码处理异常: {e}")
        return False


def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        # 为了在服务器/Docker/GitHub Actions 等环境运行，需要添加 --no-sandbox 参数
        launch_options = {
            "headless": False,  # 调试时建议设置为 False，方便观察
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
            page.wait_for_url("**/dashboard", timeout=20000)
            print("✅ 登录成功")

            # 2. 导航至续期页面
            print("🎯 进入续期页面...")
            page.goto(RENEW_URL, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            page.screenshot(path="1_server_page.png")

            # 3. 点击触发按钮
            print("🔍 定位并点击 'Renew' 按钮...")
            # 使用更简单的 CSS 选择器，通常更推荐
            trigger_button = page.locator("button.btn-primary:has-text('Renew')").first
            trigger_button.scroll_into_view_if_needed()
            trigger_button.click()
            
            # 4. 等待模态框出现
            print("🪟 等待续期弹窗加载...")
            renew_modal_title = page.locator("#renew-modal h5.modal-title:has-text('Renew')")
            renew_modal_title.wait_for(timeout=15000, state="visible")
            page.screenshot(path="2_modal_opened.png")
            print("✅ 续期弹窗已打开")

            # 5. 调用函数处理验证码
            handle_cloudflare_turnstile(page)

            # 6. 提交续期
            print("🚀 点击最终的提交按钮...")
            submit_button = page.locator("#renew-modal button.btn-primary[type='submit']").first
            submit_button.wait_for(timeout=5000, state="enabled") # 等待按钮可用
            submit_button.click()
            
            # 7. 验证结果
            print("⏳ 等待续期结果...")
            try:
                success_alert = page.locator("div.alert-success")
                success_alert.wait_for(timeout=10000)
                print(f"🎉 续期成功！消息: '{success_alert.inner_text()}'")
            except PlaywrightTimeoutError:
                print("⚠️ 未自动检测到成功提示。请检查截图或手动确认。")

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
