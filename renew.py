import asyncio
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from pathlib import Path
import os

# 配置
EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
SERVER_ID = os.getenv("KATABUMP_SERVER_ID")  # 服务器ID，如105562
HEADLESS = True  # 设置为 False 可本地调试
SCREENSHOT_DIR = Path("./screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

def take_screenshot(page, name):
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"📸 已保存截图: {name}.png")

def wait_and_click(locator, timeout=10000):
    locator.wait_for(state="visible", timeout=timeout)
    locator.click()

def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 登录
            print("🔐 打开登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=30000)

            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button:has-text("Login")')

            print("⏳ 等待跳转到 Dashboard...")
            page.wait_for_url("**/dashboard", timeout=30000)

            # 打开服务器编辑页
            print("🎯 打开服务器编辑页面...")
            edit_url = f"https://dashboard.katabump.com/servers/edit?id={SERVER_ID}"
            page.goto(edit_url, timeout=30000)
            take_screenshot(page, "before_renew")

            # 找到 Renew 按钮
            print("🟦 查找 Renew 按钮...")
            renew_btn = page.locator("button.btn.btn-primary:has-text('Renew')")
            wait_and_click(renew_btn)

            # 等待弹窗加载
            print("🪟 等待 Renew 弹窗加载...")
            modal = page.locator("#renew-modal.show")
            modal.wait_for(timeout=10000)

            # 处理 Turnstile 验证码
            print("🛡️ 查找验证码 iframe...")
            iframe_element = modal.locator("iframe[title*='Cloudflare']")
            iframe_element.wait_for(timeout=10000)

            print("🔍 查找并点击验证码 checkbox...")
            frame = iframe_element.first.content_frame()
            if frame is None:
                raise Exception("无法获取 iframe frame 内容")

            checkbox = frame.locator('input[type="checkbox"]')
            checkbox.wait_for(state="visible", timeout=10000)
            checkbox.click(force=True)

            # 等待验证码打勾成功（checkbox 变成aria-checked="true"）
            frame.locator('input[type="checkbox"][aria-checked="true"]').wait_for(timeout=10000)

            print("✅ 验证码通过，点击 Renew 提交按钮...")
            modal.locator("button.btn.btn-primary:has-text('Renew')").click()

            # 检查是否成功
            print("🕵️ 检查是否续期成功...")
            success_toast = page.locator(".Toastify__toast--success")
            success_toast.wait_for(timeout=10000)

            print("🎉 续期成功！")

        except PlaywrightTimeoutError as e:
            print(f"❌ 超时错误: {e}")
            take_screenshot(page, "timeout_error")

        except Exception as e:
            print(f"❌ 发生错误: {e}")
            take_screenshot(page, "general_error")

        finally:
            take_screenshot(page, "after_renew")
            print("🚪 关闭浏览器...")
            browser.close()

if __name__ == "__main__":
    main()