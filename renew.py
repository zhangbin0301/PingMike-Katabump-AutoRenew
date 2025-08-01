from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import os

# --- 全局变量 ---
EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=105562"


def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        # --- 解决方案: 添加 launch_options 来解决 root 用户运行问题 ---
        launch_options = {
            "headless": True, # 在服务器上运行时通常设置为 True
            "args": ["--no-sandbox"] # 关键！允许在 root 环境（如 Docker, GitHub Actions）下运行
        }
        browser = p.chromium.launch(**launch_options)
        
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. 登录流程
            print("🔐 跳转到登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=30000)
            
            print("🧾 填写登录信息...")
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            
            print("⏳ 等待跳转至 Dashboard...")
            page.wait_for_url("**/dashboard", timeout=20000)

            # 2. 续期流程
            print("🎯 跳转到服务器页面...")
            page.goto(RENEW_URL, timeout=20000)
            page.wait_for_load_state("domcontentloaded") # 等待DOM加载完成
            page.screenshot(path="before_renew.png")

            # 3. 点击触发弹窗的按钮 (使用 XPath 精准定位)
            print("🔍 查找 Renew 按钮...")
            trigger_button = page.locator(
                "//button[contains(text(), 'Renew')]"
            ).first
            trigger_button.scroll_into_view_if_needed()
            trigger_button.click()
            
            # 4. 等待弹窗出现
            print("🪟 等待续期弹窗...")
            page.wait_for_selector("h5.modal-title:has-text('Renew')", timeout=15000)
            
            # 5. 处理 Cloudflare Turnstile 验证码
            try:
                if page.locator("div.cf-turnstile").is_visible():
                    print("🛡️ 处理 Cloudflare 验证码...")
                    turnstile_iframe = page.wait_for_selector(
                        "#renew-modal iframe[title*='Cloudflare']", 
                        timeout=15000
                    )
                    frame = turnstile_iframe.content_frame()
                    checkbox = frame.locator("input[type='checkbox']")
                    checkbox.click()
                    # 等待验证完成的更好方式是等待提交按钮变为可点击状态
                    print("✅ Cloudflare 复选框已点击")
            except PlaywrightTimeoutError:
                print("⚠️ 未找到或处理 Cloudflare 验证码超时，尝试继续...")
            except Exception as e:
                print(f"⚠️ Cloudflare 处理异常: {e}")

            # 6. 提交续期
            print("🔵 点击最终的 Renew 按钮...")
            modal_button = page.locator("#renew-modal button.btn-primary[type='submit']")
            modal_button.wait_for(timeout=10000, state="visible") # 确保按钮可见
            modal_button.click()
            
            # 7. 验证结果
            print("⏳ 等待续期确认...")
            try:
                # 等待成功提示出现
                success_alert = page.locator("div.alert-success")
                success_alert.wait_for(timeout=10000)
                print(f"🎉 续期成功! 消息: {success_alert.inner_text()}")
            except PlaywrightTimeoutError:
                print("⚠️ 未检测到成功消息 (但操作可能已成功)")

            page.screenshot(path="after_renew.png")
            print("✅ 已保存截图: after_renew.png")

        except PlaywrightTimeoutError as e:
            print(f"❌ 操作超时: {e}")
            page.screenshot(path="timeout_error.png")
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            page.screenshot(path="error.png")
        finally:
            print("🚪 关闭浏览器...")
            context.close()
            browser.close()

if __name__ == "__main__":
    main()
