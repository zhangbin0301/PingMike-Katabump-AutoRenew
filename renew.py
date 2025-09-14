from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import pathlib
import re
import httpx
from typing import List, Dict

EMAIL = os.getenv("KATABUMP_EMAIL")
PASSWORD = os.getenv("KATABUMP_PASSWORD")
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=128366"

# 插件路径
EXT_PATH = str(pathlib.Path(__file__).parent / "extensions/captcha-solver")

def safe_screenshot(page, filename: str):
    try:
        page.screenshot(path=filename, full_page=True)
        print(f"📸 已保存截图: {filename}")
    except Exception as e:
        print(f"⚠️ 截图失败 {filename}: {e}")

def cookies_to_header(cookies: List[Dict]) -> str:
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)

def has_cf_cookies(cookies: List[Dict]) -> bool:
    names = [c['name'].lower() for c in cookies]
    for cf in ['__cf_bm', 'cf_clearance', 'cf_turnstile', 'cf_chl_seq']:
        if any(cf in n for n in names):
            return True
    return False

def find_api_endpoint_from_html(html: str, prefer_keywords: List[str] = None) -> str:
    """
    尝试从页面 HTML 中找第一个包含 /api/ 的路径，优先匹配 prefer_keywords（如 ['renew','attendance','server']）。
    这是 heuristic；如果你知道确切 API 路径，直接写死会更稳。
    """
    prefer_keywords = prefer_keywords or ['renew', 'attendance', 'server', 'servers', 'subscription']
    # 找到所有 /api/... 或 /v1/... 之类
    candidates = re.findall(r'(["\'])(/api[^"\']+)\1', html)
    paths = [m[1] for m in candidates]
    # 过滤重复并优先包含关键词
    seen = []
    for p in paths:
        if p not in seen:
            seen.append(p)
    for kw in prefer_keywords:
        for p in seen:
            if kw in p.lower():
                return p
    # fallback: return first found
    return seen[0] if seen else None

def send_api_request_with_cookies(full_url: str, cookie_header: str, method: str = "GET", data=None, headers_extra=None, timeout=30.0):
    """
    使用 httpx http2=True 发起请求，带上 cookie header 和常见浏览器头
    """
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": RENEW_URL,
        "Origin": "https://dashboard.katabump.com",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Dest": "empty",
        "Connection": "keep-alive",
        "Cookie": cookie_header,
    }
    if headers_extra:
        base_headers.update(headers_extra)

    with httpx.Client(http2=True, timeout=timeout) as client:
        if method.upper() == "GET":
            r = client.get(full_url, headers=base_headers)
        else:
            # 默认以 json 形式尝试发送
            r = client.post(full_url, headers=base_headers, json=data)
        return r

def main():
    print("✅ 开始执行续期任务...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                f"--disable-extensions-except={EXT_PATH}",
                f"--load-extension={EXT_PATH}",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Europe/Berlin",
        )
        page = context.new_page()

        try:
            # 登录
            print("🔐 打开登录页面...")
            page.goto("https://dashboard.katabump.com/login", timeout=30000)
            page.fill('input[name="email"]', EMAIL)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url("**/dashboard", timeout=20000)

            # 打开续期页面
            page.goto(RENEW_URL, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            safe_screenshot(page, "00_before_renew.png")

            # 点击 Renew 按钮（仍保留自动流程以触发 Turnstile iframe）
            renew_btn = page.locator("//button[contains(text(), 'Renew')]").first
            renew_btn.scroll_into_view_if_needed()
            renew_btn.click()
            page.wait_for_selector("#renew-modal.show", timeout=15000)
            safe_screenshot(page, "01_modal.png")

            # 等待 Turnstile iframe 异步加载
            print("🔍 等待 Turnstile iframe 出现...")
            page.wait_for_function(
                """
                () => Array.from(document.querySelectorAll('iframe'))
                        .some(f => f.src && f.src.includes('turnstile'))
                """,
                timeout=60000
            )
            safe_screenshot(page, "02_iframe_loaded.png")

            # 等待插件生成验证 token
            print("🤖 等待插件自动验证 Turnstile...")
            page.wait_for_function(
                """
                () => {
                    const iframeEl = Array.from(document.querySelectorAll('iframe'))
                        .find(f => f.src && f.src.includes('turnstile'));
                    if (!iframeEl) return false;
                    const innerDoc = iframeEl.contentDocument || iframeEl.contentWindow.document;
                    const token = innerDoc.querySelector('input[name="cf-turnstile-response"]');
                    return token && token.value.length > 0;
                }
                """,
                timeout=90000
            )
            safe_screenshot(page, "03_captcha_checked.png")
            print("✅ 插件已生成验证 token")

            # —— 关键：导出浏览器 cookies（含 CF 验证 cookie）并用 httpx 复用会话 —— #
            cookies = context.cookies()
            cookie_header = cookies_to_header(cookies)
            print(f"🔑 导出 cookies: {cookie_header[:200]}{'...' if len(cookie_header)>200 else ''}")
            if has_cf_cookies(cookies):
                print("🛡️ 检测到 Cloudflare 相关 cookie，说明会话经过 CF 验证。将复用此 cookie 发起 HTTP/2 请求。")
            else:
                print("⚠️ 未检测到明显的 CF cookie（可能会在服务器端触发 CF challenge）。脚本仍会尝试，但可能失败。")

            # 先用 httpx GET 一次页面，确认用同样会话能拿到页面 HTML（并尝试解析可能的 API endpoint）
            resp = send_api_request_with_cookies(RENEW_URL, cookie_header, method="GET")
            print(f"HTTP 请求状态: {resp.status_code}")
            safe_path = "05_fetch_with_cookies.html"
            with open(safe_path, "wb") as f:
                f.write(resp.content)
            print(f"📄 已保存用 cookie 请求的 HTML 到: {safe_path}")

            # 尝试从 HTML 中找第一个 /api/ 路径（heuristic）
            html = resp.text
            api_path = find_api_endpoint_from_html(html, prefer_keywords=['renew','attendance','api'])
            if api_path:
                # 构造完整 url
                api_url = api_path if api_path.startswith("http") else f"https://{page.url.split('/')[2]}{api_path}"
                print(f"🔎 发现可能的 API 地址：{api_url}")
                # 视 API 行为选择调用方式（GET/POST）。这里尝试 GET，如果需要 POST 可改成 post 并传 body
                api_resp = send_api_request_with_cookies(api_url, cookie_header, method="GET")
                print(f"-> API 调用状态: {api_resp.status_code}, 长度: {len(api_resp.content)}")
                # 若 API 返回 JSON，可进一步解析并判断是否成功
                try:
                    j = api_resp.json()
                    print("API 返回 JSON:", j)
                except Exception:
                    print("API 返回不是 JSON，已保存响应内容到文件。")
                    with open("06_api_resp.html", "wb") as f:
                        f.write(api_resp.content)
            else:
                print("⚠️ 未能从页面 HTML 中解析到 API 路径。作为备选：可以直接让 Playwright 提交 Renew 按钮（原始流程），或通过浏览器控制台观察网络请求后把 API 路径写死在脚本里。")

            # 如果你更希望直接让 Playwright 完成提交（备用）
            modal_renew_btn = page.locator("#renew-modal button.btn-primary[type='submit']")
            modal_renew_btn.wait_for(state="visible", timeout=10000)
            # 这里注释掉自动点击以避免重复触发；如果 API 重放失败，可以取消注释，使用浏览器点击：
            # modal_renew_btn.click()

            print("流程结束：已尝试用复用的 cookie 进行 HTTP/2 请求。请检查上方输出与生成的文件来确认是否完成续期。")
            safe_screenshot(page, "04_after_attempt.png")

        except PlaywrightTimeoutError as e:
            print(f"❌ 超时错误: {e}")
            safe_screenshot(page, "99_timeout_error.png")
        except Exception as e:
            print(f"❌ 异常发生: {e}")
            safe_screenshot(page, "99_exception_error.png")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()