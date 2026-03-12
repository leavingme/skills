#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过 Chrome CDP 自动获取百度网盘 BDUSS 和 STOKEN
要求：Chrome 以 --remote-debugging-port=9222 启动
"""

import os
import json
import time
import subprocess
import requests

CDP_URL = "http://127.0.0.1:9222"
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.json')
TARGET_URL = "https://pan.baidu.com"
COOKIE_NAMES = ["BDUSS", "STOKEN"]
WAIT_TIMEOUT = 60  # 等待登录最长秒数


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_cookies_via_ws(ws):
    """通过 WebSocket 读取百度网盘 Cookie"""
    req_id = int(time.time() * 1000) % 100000  # 使用稍微唯一的ID
    ws.send(json.dumps({
        "id": req_id,
        "method": "Network.getCookies",
        "params": {
            "urls": ["https://pan.baidu.com", "https://baidu.com"]
        }
    }))
    
    # 将原有 timeout 保存，循环等待特定 ID 的响应
    old_timeout = ws.gettimeout()
    ws.settimeout(2.0)
    try:
        while True:
            try:
                msg = ws.recv()
                result = json.loads(msg)
                if result.get('id') == req_id:
                    cookies = result.get('result', {}).get('cookies', [])
                    return {c['name']: c['value'] for c in cookies if c['name'] in COOKIE_NAMES}
            except Exception:
                break
    finally:
        ws.settimeout(old_timeout)
    return {}


CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def launch_chrome():
    """以 CDP 模式新开一个独立 Chrome 实例"""
    for path in CHROME_PATHS:
        if os.path.exists(path):
            print(f"正在启动新 Chrome 实例: {path}")
            # 生成一个临时目录以确保能启动独立的实例
            user_data_dir = "/tmp/chrome-debug-profile-ai"
            subprocess.Popen(
                ["open", "-na", path, "--args",
                 "--remote-debugging-port=9222", f"--user-data-dir={user_data_dir}", "--no-first-run", TARGET_URL],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # 等待 Chrome 启动并监听端口
            for _ in range(15):
                time.sleep(1)
                try:
                    requests.get(f"{CDP_URL}/json", timeout=1)
                    print("Chrome 启动成功。")
                    return True
                except Exception:
                    pass
            print("[错误] Chrome 启动超时。")
            return False
    print("[错误] 未找到 Chrome，请手动启动并添加 --remote-debugging-port=9222 参数。")
    return False


def fetch_cookies_cdp():
    print("正在连接本地 Chrome (需以 --remote-debugging-port=9222 启动)...")

    try:
        resp = requests.get(f"{CDP_URL}/json", timeout=2)
        targets = resp.json()
    except Exception:
        print("[提示] Chrome CDP 端口未开启，尝试自动启动 Chrome...")
        if not launch_chrome():
            return False
        try:
            resp = requests.get(f"{CDP_URL}/json", timeout=2)
            targets = resp.json()
        except Exception:
            print("[错误] 无法连接到 Chrome CDP 端口 9222。")
            return False

    # 查找百度网盘标签页
    baidu_target = None
    for t in targets:
        if t.get('type') == 'page' and 'pan.baidu.com' in t.get('url', ''):
            baidu_target = t
            break

    ws_url = None
    if baidu_target:
        print(f"找到百度网盘标签页: {baidu_target.get('url')}")
        ws_url = baidu_target.get('webSocketDebuggerUrl')
    else:
        print("未找到百度网盘标签页，正在指令 Chrome 打开...")
        resp = requests.put(f"{CDP_URL}/json/new?{TARGET_URL}")
        if resp.status_code == 200:
            new_target = resp.json()
            ws_url = new_target.get('webSocketDebuggerUrl')
            print(f"已打开百度网盘，请在 Chrome 窗口中完成登录（最多等待 {WAIT_TIMEOUT} 秒）...")
        else:
            print(f"[错误] 无法创建新标签页: {resp.status_code}")
            return False

    if not ws_url:
        print("[错误] 无法获取 WebSocket 调试地址。")
        return False

    try:
        import websocket
    except ImportError:
        print("[错误] 缺少 websocket-client 库，请执行：")
        print("  pip install websocket-client")
        return False

    print("已接管标签页，正在读取 Cookies...")
    ws = websocket.create_connection(ws_url, suppress_origin=True)

    # 1. 先直接尝试读取（已登录的情况）
    found = get_cookies_via_ws(ws)

    # 2. 没读到则启用网络监控 + 刷新，轮询等待登录
    if not found:
        print("当前未登录，请在 Chrome 窗口中完成登录...")
        ws.send(json.dumps({"id": 2, "method": "Network.enable"}))
        ws.recv()  # ack
        ws.send(json.dumps({"id": 3, "method": "Page.reload"}))

        start_time = time.time()
        while time.time() - start_time < WAIT_TIMEOUT:
            ws.settimeout(2.0)
            try:
                ws.recv()  # 消费事件，避免堵塞
            except websocket.WebSocketTimeoutException:
                pass

            # 每 3 秒检查一次 Cookie
            if int(time.time() - start_time) % 3 == 0:
                found = get_cookies_via_ws(ws)
                if found:
                    break
                elapsed = int(time.time() - start_time)
                print(f"  等待登录中... ({elapsed}/{WAIT_TIMEOUT}s)", end='\r')

        if not found:
            print(f"\n[超时] {WAIT_TIMEOUT} 秒内未检测到登录，请重试。")
            ws.close()
            return False

    ws.close()

    # 保存到 config.json
    config = load_config()
    for name, value in found.items():
        config[name] = value
        print(f"[成功] 已捕获 {name}")

    save_config(config)
    print(f"\n凭证已保存到 {os.path.abspath(CONFIG_PATH)}")

    missing = [n for n in COOKIE_NAMES if n not in found]
    if missing:
        print(f"[警告] 以下 Cookie 未找到，请手动填写 config.json：{missing}")
        return len(found) > 0

    print("所有凭证获取完成！")
    return True


if __name__ == "__main__":
    success = fetch_cookies_cdp()
    exit(0 if success else 1)
