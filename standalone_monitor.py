import sys
import subprocess
import time
import re
import os

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ 缺少必要的 playwright 库。正在自动为您安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright

def start_intercept():
    print("🚀 正在启动一个全新的专用 Chrome 浏览器，准备捕获接口数据...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",  # 调用本地真实的 Chrome 
            args=['--window-size=1200,800']
        )
        context = browser.new_context()
        page = context.new_page()

        print("\n=========================================================")
        print("👉 浏览器已为您自动打开并跳转到本牛云盘。")
        print("👉 第一步：请在打开的网页中【扫码或输入密码登录】。")
        print("👉 第二步：登录成功后，请直接随便点击【新建文件夹】和【新建专辑】！")
        print("👉 拦截的数据会直接打印在这里。测试完毕后您可直接关闭浏览器窗口。")
        print("=========================================================\n")

        # 监听 Request (普通版)
        def handle_request(request):
            method = request.method
            url = request.url
            if method in ["POST", "PUT"] and ("benewtech" in url or "resources-app" in url):
                # 过滤掉图片或心跳日志
                if "web/albums" in url or "web/folders" in url or "cloud/web" in url:
                    try:
                        post_data = request.post_data
                        print(f"\n📡 [拦截到接口]: {method} {url}")
                        if post_data:
                            print(f"📦 [提交的载荷 (Payload)]: {post_data}")
                    except Exception:
                        pass
        
        page.on("request", handle_request)
        
        # 导航到本牛云盘
        page.goto("https://pan.benewtech.cn")

        # 堵塞，直到在这个窗口里手动关闭浏览器为止。
        try:
            page.wait_for_timeout(300000) # 保持开启 5 分钟
        except Exception as e:
            print("浏览器已被关闭或停止执行。")
        finally:
            try:
                browser.close()
            except:
                pass
            print("🏁 程序已经安全退出。")

if __name__ == "__main__":
    start_intercept()
