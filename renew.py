import os
import platform
from seleniumbase import SB
from pyvirtualdisplay import Display

EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")

LOGIN_URL = "https://dashboard.katabump.com/login"
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=218445"

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def setup_xvfb():
    if platform.system().lower() == "linux" and not os.environ.get("DISPLAY"):
        display = Display(visible=False, size=(1920, 1080))
        display.start()
        os.environ["DISPLAY"] = display.new_display_var
        print("🖥️ Xvfb 已启动")
        return display
    return None


def screenshot(sb, name):
    path = f"{SCREENSHOT_DIR}/{name}"
    sb.save_screenshot(path)
    print(f"📸 截图保存: {path}")


def get_expiry(sb):
    return sb.get_text(
        "//div[contains(text(),'Expiry')]/following-sibling::div"
    ).strip()


def main():
    if not EMAIL or not PASSWORD:
        raise RuntimeError("❌ 缺少账号环境变量")

    display = setup_xvfb()

    try:
        with SB(uc=True, headless=True, locale="en") as sb:
            print("🚀 启动浏览器")

            # ========= 登录 =========
            sb.open(LOGIN_URL)
            sb.type('input[name="email"]', EMAIL)
            sb.type('input[name="password"]', PASSWORD)
            sb.click('button[type="submit"]')
            sb.wait_for_element_visible("body", timeout=20)

            # ========= 打开续期页面 =========
            sb.open(RENEW_URL)
            sb.wait_for_element_visible("body", timeout=20)
            screenshot(sb, "01_before_renew.png")

            old_expiry = get_expiry(sb)
            print("📅 旧 Expiry:", old_expiry)

            # ========= 打开 Renew Modal =========
            sb.click("button:contains('Renew')")
            sb.wait_for_element_visible("#renew-modal", timeout=20)
            screenshot(sb, "02_modal_open.png")

            # ========= Turnstile =========
            try:
                sb.uc_gui_click_captcha()
                sb.sleep(3)
            except Exception as e:
                print(f"⚠️ Turnstile 点击异常（可能被 CF 静默拦截）: {e}")

            screenshot(sb, "03_after_turnstile.png")

            # ========= 获取 Turnstile token（修复版） =========
            token = sb.execute_script("""
(() => {
  const el = document.querySelector("input[name='cf-turnstile-response']");
  return el ? el.value : null;
})()
""")

            print("🧩 Turnstile token:", token)

            if not token:
                screenshot(sb, "04_turnstile_failed.png")
                print("❌ Turnstile 未通过，Cloudflare 阻止了自动化")
                return

            # ========= 提交 form（关键） =========
            sb.execute_script("""
document.querySelector('#renew-modal form').submit();
""")

            sb.sleep(2)
            screenshot(sb, "05_after_submit.png")

            # ========= 刷新并验证 Expiry =========
            sb.refresh()
            sb.wait_for_element_visible("body", timeout=20)
            screenshot(sb, "06_after_refresh.png")

            new_expiry = get_expiry(sb)
            print("📅 新 Expiry:", new_expiry)

            if new_expiry == old_expiry:
                print("❌ Expiry 未变化，续期失败")
                return

            print("🎉 续期真实成功")

    finally:
        if display:
            display.stop()


if __name__ == "__main__":
    main()