import os
import re
from playwright.sync_api import sync_playwright

ENV_PATH = os.path.join(os.getcwd(), ".env.benew")

def update_env(key, value):
    content = ""
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            content = f.read()

    if f"{key}=" in content:
        content = re.sub(f'{key}=[\'"].*?[\'"]', f'{key}={repr(value)}', content)
    else:
        content += f'\n{key}={repr(value)}\n'

    with open(ENV_PATH, "w") as f:
        f.write(content)
    print(f"[Success] 已将 {key} 提取并更新到 {ENV_PATH}")


def fetch_credentials():
    print("正在启动浏览器窗口 (请在弹出的界面登录本牛云盘，并随便点击一下你的任意专辑)...")
    with sync_playwright() as p:
        # Use local Google Chrome installation
        browser = p.chromium.launch(
            headless=False,
            channel="chrome"
        )
        context = browser.new_context()
        page = context.new_page()

        captured_family_id = None

        def handle_request(request):
            nonlocal captured_family_id
            if captured_family_id:
                return
            # Extract familyId from query params, e.g. "?familyId=3056748"
            match = re.search(r'familyId=(\d+)', request.url)
            if match:
                captured_family_id = match.group(1)
                update_env("FAMILY_ID", captured_family_id)

        page.on("request", handle_request)

        page.goto("https://pan.benewtech.cn")
        print("[Wait] 已打开本牛云盘。请扫码或输入密码登录。后台正在监听 Cookie 和 Family ID...")

        target_cookie_name = "connect.sid"
        captured_cookie = None

        # Loop until we find the cookie and family id, or until timeout
        for _ in range(600):  # Maximum wait time 60 seconds
            if not captured_cookie:
                cookies = context.cookies()
                for c in cookies:
                    if c["name"] == target_cookie_name:
                        captured_cookie = f"{c['name']}={c['value']}"
                        update_env("COOKIE", captured_cookie)
                        break

            # If both are captured, we can exit early.
            # However, familyId might only be sent when user clicks an album.
            # We'll wait a bit longer if we only got Cookie but no FamilyID.
            if captured_cookie and captured_family_id:
                break
                
            page.wait_for_timeout(100)
            
        if captured_cookie:
            if not captured_family_id:
                print("Cookie已获取，但未捕捉到 familyId 请求。如果您后续仍缺 FAMILY_ID，可以在代码里或者网络请求中抓取。")
            print("抓取完成，即将关闭浏览器，脚本退出。")
        else:
            print("[Timeout] 超过60秒未检测到登录成功的 Cookie，脚本退出。")

        # Let the user have 2 more seconds if they want to see
        page.wait_for_timeout(2000)
        browser.close()

if __name__ == "__main__":
    fetch_credentials()
