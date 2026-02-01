import os
import time
import platform
from seleniumbase import SB
from pyvirtualdisplay import Display


EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")

LOGIN_URL = "https://dashboard.katabump.com/login"
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=218445"


def setup_xvfb():
    if platform.system().lower() == "linux" and not os.environ.get("DISPLAY"):
        display = Display(visible=False, size=(1920, 1080))
        display.start()
        os.environ["DISPLAY"] = display.new_display_var
        print("🖥️ Xvfb 已启动")
        return display
    return None


def main():
    if not EMAIL or not PASSWORD:
        raise RuntimeError("❌ 缺少账号环境变量")

    display = setup_xvfb()

    try:
        with SB(
            uc=True,
            headless=True,
            locale="en",
        ) as sb:
            print("🚀 启动浏览器")

            # 登录
            print("🔐 登录 katabump")
            sb.open(LOGIN_URL)
            sb.type('input[name="email"]', EMAIL)
            sb.type('input[name="password"]', PASSWORD)
            sb.click('button[type="submit"]')
            sb.wait_for_element_visible("body", timeout=20)

            # 打开续期页面
            print("🔁 打开续期页面")
            sb.open(RENEW_URL)
            sb.sleep(2)

            # 点击 Renew
            print("🖱️ 点击 Renew")
            sb.find_element("//button[contains(text(),'Renew')]").click()
            sb.wait_for_element_visible("#renew-modal", timeout=20)

            # 🔥 关键：此时才处理 Turnstile
            print("🛡️ 处理 Turnstile（确认框）")
            try:
                sb.uc_gui_click_captcha()
                sb.sleep(4)
            except Exception as e:
                print(f"⚠️ Turnstile 点击异常（可能已自动通过）: {e}")

            # 点击最终确认 Renew
            print("✅ 提交 Renew")
            sb.click("#renew-modal button.btn-primary[type='submit']")

            # 等成功提示（比 alert-success 更稳）
            sb.wait_for_text_visible("success", timeout=20)
            print("🎉 续期成功")

    finally:
        if display:
            display.stop()


if __name__ == "__main__":
    main()