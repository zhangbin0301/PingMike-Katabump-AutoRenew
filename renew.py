import os
import time
import platform
from typing import Dict

from seleniumbase import SB
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")

LOGIN_URL = "https://dashboard.katabump.com/login"
HOME_URL = "https://dashboard.katabump.com/"
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=218445"


# ============================================================
# Linux (GitHub Actions) 虚拟显示
# ============================================================
def setup_xvfb():
    if platform.system().lower() == "linux" and not os.environ.get("DISPLAY"):
        from pyvirtualdisplay import Display
        display = Display(visible=False, size=(1920, 1080))
        display.start()
        os.environ["DISPLAY"] = display.new_display_var
        print("🖥️ Xvfb 已启动")
        return display
    return None


# ============================================================
# Step 1: SeleniumBase UC 过 Cloudflare
# ============================================================
def get_cf_session() -> Dict:
    print("🛡️ SeleniumBase UC 绕过 Cloudflare")

    with SB(
        uc=True,
        headless=True,
        locale="en",
        disable_csp=True,
    ) as sb:
        sb.uc_open_with_reconnect(HOME_URL, reconnect_time=5)
        time.sleep(3)

        page = sb.get_page_source().lower()
        if any(x in page for x in ["cloudflare", "turnstile", "just a moment"]):
            print("🔍 检测到 CF，尝试自动验证")
            try:
                sb.uc_gui_click_captcha()
                time.sleep(5)
            except Exception as e:
                print(f"⚠️ 验证点击异常（可能不需要）: {e}")

        cookies = sb.get_cookies()
        ua = sb.execute_script("return navigator.userAgent")
        cookie_map = {c["name"]: c["value"] for c in cookies}

        if "cf_clearance" not in cookie_map:
            raise RuntimeError("❌ 未获取 cf_clearance（IP 可能被风控）")

        print("✅ cf_clearance 获取成功")
        return {"cookies": cookies, "user_agent": ua}


# ============================================================
# Step 2: Playwright 注入 Cookie，执行续期
# ============================================================
def renew_with_playwright(cf_data: Dict):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
        )

        context = browser.new_context(
            user_agent=cf_data["user_agent"],
            locale="en-US",
            viewport={"width": 1280, "height": 800},
        )

        context.add_cookies([
            {
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c.get("path", "/"),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
            }
            for c in cf_data["cookies"]
        ])

        page = context.new_page()

        try:
            print("🔐 登录 katabump")
            page.goto(LOGIN_URL, timeout=30000)
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url("**/dashboard", timeout=20000)

            print("🔁 打开续期页面")
            page.goto(RENEW_URL, timeout=20000)
            page.wait_for_load_state("domcontentloaded")

            renew_btn = page.locator("//button[contains(text(), 'Renew')]").first
            renew_btn.scroll_into_view_if_needed()
            renew_btn.click()

            page.wait_for_selector("#renew-modal.show", timeout=15000)

            print("✅ 已绕过 CF，提交续期")
            submit_btn = page.locator(
                "#renew-modal button.btn-primary[type='submit']"
            )
            submit_btn.wait_for(state="visible", timeout=10000)
            submit_btn.click()

            success = page.locator("div.alert-success")
            success.wait_for(timeout=15000)

            print("🎉 续期成功")
            print(success.inner_text())

        except PlaywrightTimeoutError as e:
            raise RuntimeError(f"❌ Playwright 超时: {e}")
        finally:
            context.close()
            browser.close()


def main():
    if not EMAIL or not PASSWORD:
        raise RuntimeError("❌ 未设置 KATABUMP_EMAIL / PASSWORD")

    display = setup_xvfb()

    try:
        cf_data = get_cf_session()
        renew_with_playwright(cf_data)
    finally:
        if display:
            display.stop()


if __name__ == "__main__":
    main()