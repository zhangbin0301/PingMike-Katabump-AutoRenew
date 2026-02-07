import os
import platform
import time
import requests
from datetime import datetime, timedelta
from seleniumbase import SB
from pyvirtualdisplay import Display

# ===== 环境变量配置 =====
EMAIL = os.getenv("KATABUMP_EMAIL") or ""
PASSWORD = os.getenv("KATABUMP_PASSWORD") or ""

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or ""

LOGIN_URL = "https://dashboard.katabump.com/login"
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=220210"

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def send_tg_msg(message: str):
    """通过 Telegram Bot 发送消息"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 未配置 TG 环境变量，跳过通知")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🤖 **Katabump 续期通知**\n{message}",
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ TG 发送失败: {e}")

def setup_xvfb():
    """在 Linux 上启动 Xvfb"""
    if platform.system().lower() == "linux" and not os.environ.get("DISPLAY"):
        display = Display(visible=False, size=(1920, 1080))
        display.start()
        os.environ["DISPLAY"] = display.new_display_var
        print("🖥️ Xvfb 已启动")
        return display
    return None

def screenshot(sb, name: str):
    """保存截图"""
    path = f"{SCREENSHOT_DIR}/{name}"
    sb.save_screenshot(path)
    print(f"📸 {path}")

def get_expiry(sb) -> str:
    """获取服务器 Expiry 字符串"""
    return sb.get_text(
        "//div[contains(text(),'Expiry')]/following-sibling::div"
    ).strip()

def parse_expiry_date(expiry_str: str) -> datetime:
    """把 Expiry 字符串解析为 datetime"""
    return datetime.strptime(expiry_str, "%Y-%m-%d")

def should_renew(expiry_str: str) -> bool:
    """判断是否到续期时间（到期前一天）"""
    # expiry_date = parse_expiry_date(expiry_str)
    # today = datetime.today()
    expiry_date = parse_expiry_date(expiry_str).date()
        today = datetime.today().date()

    delta_days = (expiry_date - today).days
    print(f"📅 到期日期: {expiry_date}, 今日日期: {today}, 相差天数: {delta_days}")
    
    # return (expiry_date - today).days == 1
    return delta_days == 1

def main():
    if not EMAIL or not PASSWORD:
        raise RuntimeError("❌ 缺少账号环境变量")

    display = setup_xvfb()

    try:
        with SB(uc=True, locale="en", test=True) as sb:
            print("🚀 浏览器启动（UC Mode）")

            # ===== 登录 =====
            sb.uc_open_with_reconnect(LOGIN_URL, reconnect_time=5.0)
            time.sleep(2)
            sb.type('input[name="email"]', EMAIL)
            sb.type('input[name="password"]', PASSWORD)
            sb.click('button[type="submit"]')
            sb.wait_for_element_visible("body", timeout=30)
            time.sleep(2)

            # ===== 打开续期页 =====
            sb.uc_open_with_reconnect(RENEW_URL, reconnect_time=5.0)
            sb.wait_for_element_visible("body", timeout=30)
            time.sleep(2)
            screenshot(sb, "01_page_loaded.png")

            # ===== 获取 Expiry 并检查是否需要续期 =====
            expiry_str = get_expiry(sb)
            print(f"📅 当前 Expiry: {expiry_str}")

            # ===== 逻辑判定 =====
            if not should_renew(expiry_str):
                idle_msg = (
                    f"ℹ️ *Katabump 状态检查*\n"
                    f"📅 当前到期: `{expiry_str}`\n"
                    f"⏳ 还没到续期时间，今天不操作。"
                )
                print("ℹ️ 还没到续期时间，今天不干活，溜了溜了")
                send_tg_msg(idle_msg)
                return

            print("🔔 到续期时间，开始续期流程...")

            # ===== 打开 Renew Modal =====
            sb.click("button:contains('Renew')")
            sb.wait_for_element_visible("#renew-modal", timeout=20)
            time.sleep(2)
            screenshot(sb, "02_modal_open.png")

            # ===== 尝试 Turnstile 交互 =====
            try:
                sb.uc_gui_click_captcha()
                time.sleep(4)
            except Exception as e:
                print(f"⚠️ captcha 点击异常: {e}")

            screenshot(sb, "03_after_captcha.png")

            # ===== 检查 cookies =====
            cookies = sb.get_cookies()
            cookie_names = [c["name"] for c in cookies]
            print("🍪 Cookies:", cookie_names)

            cf_clearance = next(
                (c["value"] for c in cookies if c["name"] == "cf_clearance"),
                None
            )
            print("🧩 cf_clearance:", cf_clearance)

            if not cf_clearance:
                screenshot(sb, "04_no_cf_clearance.png")
                print("❌ 未获取 cf_clearance，续期可能失败")
                return

            # ===== 提交 Renew =====
            sb.execute_script("document.querySelector('#renew-modal form').submit();")
            print("⏳ 提交成功，等待服务器处理数据（10秒）...")
            time.sleep(10)
            screenshot(sb, "05_after_submit.png")

            #sb.refresh()
            print("🔄 正在强制刷新页面以获取最新日期...")
            sb.execute_script("location.reload(true);")
            time.sleep(5)
            new_expiry = get_expiry(sb)
            
            # 二次补偿机制：如果日期没变，再执行一次普通刷新
            if new_expiry == expiry_str:
                print("⚠️ 日期未更新，尝试第二次刷新...")
                sb.refresh()
                time.sleep(5)
                new_expiry = get_expiry(sb)            
            
            final_msg = (
                f"✅ *Katabump 续期成功*\n"
                f"📅 *原到期日:* `{expiry_str}`\n"
                f"📅 *新到期日:* `{new_expiry}`\n"
                f"⏰ *执行时间:* {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            print(final_msg)
            send_tg_msg(final_msg)

    except Exception as e:
        fail_msg = f"💥 *Katabump 脚本出错*\n❌ 错误信息: `{str(e)}`"
        send_tg_msg(fail_msg)    

    finally:
        if display: display.stop()

if __name__ == "__main__":
    main()
