import os
import re
import time
import requests

ENV_PATH = os.path.join(os.getcwd(), ".env.benew")
CDP_URL = "http://127.0.0.1:9222"

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

def fetch_credentials_cdp():
    print("正在尝试连接本地已运行的 Chrome 实例 (要求以 --remote-debugging-port=9222 启动)...")
    
    try:
        # 获取所有打开的标签页
        resp = requests.get(f"{CDP_URL}/json", timeout=2)
        targets = resp.json()
    except Exception as e:
        print(f"[Warning] 无法连接到本地 Chrome 的 CDP 端口 9222。可能是您的 Chrome 没有使用该参数开启。")
        print("======> [Fallback] 因为端口未开启，现在尝试降级使用 Playwright 弹出独立窗口的方式来抓取！ <======")
        try:
            import get_cookie
            get_cookie.fetch_credentials()
        except ImportError:
            print("未能找到退路脚本 get_cookie.py 或尚未安装 Playwright，脚本终止。")
        return False

    # 寻找本牛云盘的标签页
    benew_target = None
    for t in targets:
        if t.get('type') == 'page' and "benewtech.cn" in t.get('url', ''):
            benew_target = t
            break

    ws_url = None
    if benew_target:
        print(f"找到本牛云盘标签页: {benew_target.get('url')}")
        ws_url = benew_target.get('webSocketDebuggerUrl')
    else:
        # 如果没找到，就在 Chrome 里新开一个标签页
        print("未找到本牛云盘标签页，正在指令 Chrome 打开新标签页...")
        resp = requests.put(f"{CDP_URL}/json/new?https://pan.benewtech.cn")
        if resp.status_code == 200:
            new_target = resp.json()
            ws_url = new_target.get('webSocketDebuggerUrl')
        else:
            print(f"无法创建新标签页: {resp.status_code}")
            return False

    if not ws_url:
        print("无法获取 WebSocket 调试地址。")
        return False

    print("已接管网页，正在读取 Cookies 和网络请求参数...")
    
    # 使用 websocket 库与 Chrome 通信
    # 轻量级实现，如果不希望引入 websocket-client，可以在这之前让 AI 提示安装
    try:
        import websocket
    except ImportError:
        print("缺少 websocket-client 库。正在尝试通过终端提示您或自动安装...")
        print("请执行: pip install websocket-client 然后重试。")
        return False

    ws = websocket.create_connection(ws_url, suppress_origin=True)
    
    # 1. 直接获取网页上的所有 Cookie (不需要刷新)
    # 发送 Network.getCookies 命令
    ws.send(json.dumps({
        "id": 1,
        "method": "Network.getCookies",
        "params": {
            "urls": ["https://pan.benewtech.cn", "https://gateway.benewtech.cn"]
        }
    }))
    
    result = json.loads(ws.recv())
    cookies = result.get('result', {}).get('cookies', [])
    
    captured_cookie = None
    for c in cookies:
        if c['name'] == 'connect.sid':
            captured_cookie = f"{c['name']}={c['value']}"
            update_env("COOKIE", captured_cookie)
            print("成功通过 Chrome CDP 静默捕获 Cookie!")
            break

    if not captured_cookie:
        print("当前本牛云盘暂未登录或未发现有效 Cookie。请在当前你自己的 Chrome 窗口中进行扫码/登录。")
        
    print("现在监听网络请求以捕获 FAMILY_ID...")
    # 2. 启用网络监控以拦截 familyId
    ws.send(json.dumps({"id": 2, "method": "Network.enable"}))
    ws.recv() # ack
    
    captured_family_id = None
    start_time = time.time()
    
    print("等待捕获中... (请在刚才打开的 Chrome 界面里随便点击一下你自己的任意一个专辑以触发数据包)")
    # 最多等60秒
    while time.time() - start_time < 60:
        ws.settimeout(1.0)
        try:
            msg = json.loads(ws.recv())
            if msg.get('method') == 'Network.requestWillBeSent':
                req_url = msg['params']['request']['url']
                match = re.search(r'familyId=(\d+)', req_url)
                if match:
                    captured_family_id = match.group(1)
                    update_env("FAMILY_ID", captured_family_id)
                    print(f"成功通过 Chrome CDP 拦截到网络请求，捕获 FAMILY_ID: {captured_family_id}")
                    break
        except websocket.WebSocketTimeoutException:
            continue
            
    ws.close()
    
    if captured_cookie and captured_family_id:
        print("所有必要凭证捕获完成!")
    else:
        print("捕获结束，仍存在未获取的凭证。如果 Cookie 已经捕获成功，你可以手动去 .env 填写剩余的参数。")
    return True

if __name__ == "__main__":
    import json
    fetch_credentials_cdp()
