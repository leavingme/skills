"""
腾讯会议 CDP 凭证同步公共模块。

通过 Chrome DevTools Protocol 从浏览器中提取 Cookie，
供所有脚本复用，避免重复的 WebSocket 连接逻辑。

CDP 连接策略（Chrome 146+）:
  1. 读取 DevToolsActivePort 文件（Chrome 默认生成）+ 验证端口可达
  2. Chrome 未运行时 → 自动启动 Chrome，等待 DevToolsActivePort 文件就绪

注意: Chrome 146+ 首次 CDP 连接时会在浏览器弹出确认对话框，
      需要用户点击「允许」后才能完成 WebSocket 握手。
      因此 open_timeout 设为 30 秒。
"""

import json
import asyncio
import websockets
import os
import sys
import time
import uuid
import random
import string
import subprocess
import platform
import socket
import requests


# ── 常量 ──────────────────────────────────────────────
CORP_ID = "1400115281"
MEETING_RECORD_URL = "meeting.tencent.com/user-center/meeting-record"
MEETING_RECORD_FULL_URL = "https://meeting.tencent.com/user-center/meeting-record"
MEETING_DOMAIN = "meeting.tencent.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"

# Chrome 应用路径 (macOS)
CHROME_APP_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Chrome 最低版本要求
CHROME_MIN_VERSION = 146
# CDP WebSocket 连接超时（秒），首次连接需用户在 Chrome 上确认
CDP_OPEN_TIMEOUT = 30
# DevToolsActivePort 文件路径
DEVTOOLS_PORT_FILE = os.path.expanduser(
    '~/Library/Application Support/Google/Chrome/DevToolsActivePort'
)
# Cookie 缓存文件路径和有效期（秒）
COOKIE_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cookie_cache.json")
COOKIE_CACHE_TTL = 7200  # 2 小时


def _gen_params(**extra):
    """生成通用的 URL query 参数（时间戳、nonce、trace-id 等）。"""
    params = {
        "c_os": "web",
        "c_timestamp": str(int(time.time() * 1000)),
        "c_nonce": ''.join(random.choices(string.ascii_letters + string.digits, k=9)),
        "trace-id": uuid.uuid4().hex,
        "c_instance_id": "5",
        "c_account_corp_id": CORP_ID,
        "c_lang": "zh-CN",
    }
    params.update(extra)
    return params


def _base_headers(cookie_str, caller="my_meetings"):
    """生成通用请求头。"""
    return {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Cookie": cookie_str,
        "Web-Caller": caller,
        "Referer": f"https://{MEETING_DOMAIN}/user-center/meeting-record",
        "User-Agent": UA,
        "Origin": f"https://{MEETING_DOMAIN}",
    }


# ── Cookie 缓存 ──────────────────────────────────────


def _save_cookie_cache(cookie_str):
    """将 Cookie 写入本地缓存文件。"""
    try:
        data = {"cookie": cookie_str, "timestamp": time.time()}
        with open(COOKIE_CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _load_cookie_cache():
    """
    从本地缓存读取 Cookie。
    返回 cookie_str（未过期且存在时），否则返回 None。
    """
    try:
        if not os.path.exists(COOKIE_CACHE_FILE):
            return None
        with open(COOKIE_CACHE_FILE, "r") as f:
            data = json.load(f)
        if time.time() - data.get("timestamp", 0) > COOKIE_CACHE_TTL:
            return None
        return data.get("cookie")
    except Exception:
        return None


def _validate_cookie(cookie_str):
    """
    用一个轻量级 API 调用验证 Cookie 是否仍然有效。
    返回 True/False。
    """
    url = "https://meeting.tencent.com/wemeet-tapi/v2/meetlog/dashboard/my-record-list"
    headers = _base_headers(cookie_str)
    params = _gen_params()
    payload = {
        "begin_time": "0", "end_time": "0", "meeting_code": "",
        "page_index": 1, "page_size": 1,
        "aggregationFastRecording": 0,
        "cover_image_type": "meetlog_list_webp",
        "record_type_v4": RECORD_TYPE_FILTER,
        "sort_by": "uni_record_id", "record_scene": 1,
    }
    try:
        resp = requests.post(url, headers=headers, params=params, json=payload, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("code") == 0
    except Exception:
        pass
    return False


# ── CDP 连接辅助 ──────────────────────────────────────


def _get_chrome_version_from_binary():
    """
    通过 Chrome 可执行文件获取版本号（不依赖 CDP 连接）。
    返回版本字符串如 "146.0.7680.80"，或 None。
    """
    try:
        if platform.system() == "Darwin" and os.path.exists(CHROME_APP_PATH):
            result = subprocess.run(
                [CHROME_APP_PATH, "--version"],
                capture_output=True, text=True, timeout=5
            )
            # 输出格式: "Google Chrome 146.0.7680.80"
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                for part in parts:
                    if part[0].isdigit():
                        return part
    except Exception:
        pass
    return None


def _parse_major_version(version_str):
    """
    从版本字符串中提取主版本号。
    支持格式: "Chrome/146.0.7680.80", "146.0.7680.80", "Google Chrome 146.0.7680.80"
    返回 int 或 None。
    """
    if not version_str:
        return None
    # 去除前缀 "Chrome/" 或 "Google Chrome "
    for prefix in ("Chrome/", "Google Chrome "):
        if prefix in version_str:
            version_str = version_str.split(prefix)[-1]
    try:
        return int(version_str.split(".")[0])
    except (ValueError, IndexError):
        return None


def _check_chrome_version(version_str=None):
    """
    检查 Chrome 版本是否满足最低要求 (>= CHROME_MIN_VERSION)。

    参数:
        version_str: 版本字符串。如果为 None 则尝试从二进制获取。

    异常:
        RuntimeError: 版本过低时抛出
    """
    if not version_str:
        version_str = _get_chrome_version_from_binary()

    major = _parse_major_version(version_str)
    if major is None:
        # 无法判断版本，打印警告但不阻塞
        print(f"⚠️  无法检测 Chrome 版本（获取到: {version_str!r}），建议确认版本 >= {CHROME_MIN_VERSION}")
        return

    if major < CHROME_MIN_VERSION:
        raise RuntimeError(
            f"❌ Chrome 版本过低: 当前为 {version_str}（主版本 {major}），"
            f"需要 {CHROME_MIN_VERSION} 及以上。\n"
            "\n"
            "请更新 Chrome 浏览器：\n"
            "  1. 打开 Chrome → 菜单 → 帮助 → 关于 Google Chrome\n"
            "  2. 或直接访问 chrome://settings/help\n"
            "  3. 等待自动更新完成后重启 Chrome"
        )

    print(f"✅ Chrome 版本检查通过: {version_str}（>= {CHROME_MIN_VERSION}）")


def _read_port_file():
    """
    从 DevToolsActivePort 文件读取 WebSocket URL。
    返回 (ws_url, port_num) 元组，或 (None, None)。
    """
    if not os.path.exists(DEVTOOLS_PORT_FILE):
        return None, None
    try:
        with open(DEVTOOLS_PORT_FILE, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 2:
                port = int(lines[0].strip())
                path = lines[1].strip()
                return f"ws://127.0.0.1:{port}{path}", port
    except Exception:
        pass
    return None, None


def _is_port_reachable(port, timeout=2):
    """用 TCP socket 快速探测端口是否可达。"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(("127.0.0.1", port))
        sock.close()
        return True
    except (socket.error, socket.timeout, OSError):
        return False


def _is_chrome_running():
    """
    检查 Google Chrome 主进程是否正在运行。
    精确匹配 Chrome 可执行文件路径，避免误判其他 Electron 应用。
    """
    try:
        result = subprocess.run(
            ["pgrep", "-f", CHROME_APP_PATH],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def _launch_chrome():
    """
    启动 Chrome 浏览器（不指定端口，Chrome 146+ 默认生成 DevToolsActivePort）。

    返回:
        ws_url: WebSocket debugger URL，或 None 表示失败
    """
    # 记录旧 port file 内容，用于判断是否已刷新
    old_ws_url, _ = _read_port_file()

    print("🔧 正在启动 Chrome ...")

    if platform.system() == "Darwin":
        subprocess.Popen(
            ["open", "-a", "Google Chrome"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    else:
        subprocess.Popen(
            ["google-chrome"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    # 等待 DevToolsActivePort 文件刷新（最多 20 秒）
    print("⏳ 等待 Chrome 就绪...")
    for i in range(40):
        time.sleep(0.5)
        ws_url, port = _read_port_file()
        if ws_url and port and _is_port_reachable(port):
            # 确保 port file 已更新（不是旧文件残留）
            if ws_url != old_ws_url:
                # 端口可达且文件已更新，再等一小会让 WebSocket 完全就绪
                time.sleep(1)
                print(f"✅ Chrome 已就绪 (端口 {port})")
                return ws_url
            # 如果 ws_url 和旧的一样但端口可达，可能是 port 碰巧复用
            # 也尝试一下
            if i > 10:  # 等了 5 秒还是旧内容但端口通了，就用它
                time.sleep(1)
                print(f"✅ Chrome 已就绪 (端口 {port})")
                return ws_url

    return None


def _get_ws_url(auto_launch=True):
    """
    获取 Chrome CDP WebSocket URL。

    策略:
      1. DevToolsActivePort 文件 + 验证 Chrome 运行中 + 端口可达
      2. (可选) 自动启动 Chrome，等待 DevToolsActivePort 就绪

    连接成功后会自动检查 Chrome 版本（>= CHROME_MIN_VERSION）。

    参数:
        auto_launch: 连接失败时是否自动启动 Chrome

    返回:
        ws_url: WebSocket URL

    异常:
        RuntimeError: 无法连接到 Chrome 或版本过低
    """
    # 先检查版本
    _check_chrome_version()

    # 策略 1: DevToolsActivePort 文件
    ws_url, port = _read_port_file()
    if ws_url and port:
        if not _is_chrome_running():
            print("⚠️  DevToolsActivePort 文件存在但 Chrome 未运行，文件已过期，跳过...")
        elif not _is_port_reachable(port):
            print(f"⚠️  DevToolsActivePort 端口 {port} 不可达，尝试其他方式...")
        else:
            print(f"✅ 通过 DevToolsActivePort 连接 (端口 {port})")
            return ws_url

    # 策略 2: 自动启动 Chrome
    if auto_launch:
        if _is_chrome_running():
            # Chrome 在运行但 port file 无效 — 可能需要重启
            print("⚠️  Chrome 正在运行但无法通过 DevToolsActivePort 连接。")
            print("   请尝试完全关闭 Chrome（Cmd+Q）后重新运行脚本。")
            print()
        else:
            print("⚠️  Chrome 未运行，正在启动...")
            ws_url = _launch_chrome()
            if ws_url:
                return ws_url

    # 所有策略都失败
    raise RuntimeError(
        "❌ 无法连接到 Chrome DevTools Protocol。\n"
        "\n"
        "请按以下步骤操作：\n"
        f"  1. 确认 Chrome 版本 >= {CHROME_MIN_VERSION}（chrome://settings/help）\n"
        "  2. 完全关闭 Chrome（Cmd+Q）\n"
        "  3. 重新打开 Chrome\n"
        "  4. 登录腾讯会议并打开录制列表页\n"
        "  5. 重新运行本脚本"
    )


async def _ensure_meeting_target(ws):
    """
    确保浏览器中存在腾讯会议页面 target。

    如果找不到，则通过 CDP 自动打开录制列表页。
    返回目标 target 信息字典。
    """
    await ws.send(json.dumps({"method": "Target.getTargets", "id": 1}))
    msg = json.loads(await ws.recv())
    targets = msg.get("result", {}).get("targetInfos", [])

    # 优先查找录制列表页
    target = next(
        (t for t in targets if MEETING_RECORD_URL in t.get("url", "")),
        None
    )
    # 其次查找任意腾讯会议页面
    if not target:
        target = next(
            (t for t in targets if MEETING_DOMAIN in t.get("url", "")),
            None
        )

    if target:
        return target

    # 未找到 → 自动打开录制列表页
    print(f"📋 未在浏览器中找到腾讯会议页面，正在自动打开录制列表...")
    await ws.send(json.dumps({
        "method": "Target.createTarget",
        "params": {"url": MEETING_RECORD_FULL_URL},
        "id": 100
    }))
    create_msg = json.loads(await ws.recv())
    new_target_id = create_msg.get("result", {}).get("targetId")

    if not new_target_id:
        raise RuntimeError(
            "❌ 无法创建新标签页。\n"
            f"请手动在 Chrome 中打开 {MEETING_RECORD_FULL_URL}"
        )

    # 等待页面加载
    print("⏳ 等待页面加载...")
    await asyncio.sleep(5)

    # 重新获取 targets
    await ws.send(json.dumps({"method": "Target.getTargets", "id": 101}))
    msg = json.loads(await ws.recv())
    targets = msg.get("result", {}).get("targetInfos", [])

    target = next(
        (t for t in targets if t.get("targetId") == new_target_id),
        None
    )
    if not target:
        target = next(
            (t for t in targets if MEETING_DOMAIN in t.get("url", "")),
            None
        )
    if not target:
        raise RuntimeError(
            "❌ 已打开录制页面但无法获取 target。\n"
            f"请手动在 Chrome 中确认 {MEETING_RECORD_FULL_URL} 已加载。"
        )

    print(f"✅ 录制页面已打开: {target.get('url', '')[:80]}")
    return target


async def _attach_and_get_cookies(ws, target):
    """
    附加到目标 target 并获取 tencent.com 域下的 Cookie 字符串。
    """
    await ws.send(json.dumps({
        "method": "Target.attachToTarget",
        "params": {"targetId": target["targetId"], "flatten": True},
        "id": 2
    }))
    session_id = None
    while True:
        m = json.loads(await ws.recv())
        if m.get("id") == 2:
            session_id = m["result"]["sessionId"]
            break
        if m.get("method") == "Target.attachedToTarget":
            session_id = m["params"]["sessionId"]
            break

    await ws.send(json.dumps({
        "sessionId": session_id,
        "method": "Network.getAllCookies",
        "id": 3
    }))
    while True:
        m = json.loads(await ws.recv())
        if m.get("id") == 3:
            cookies = m["result"]["cookies"]
            cookie_str = "; ".join(
                f"{c['name']}={c['value']}"
                for c in cookies if "tencent.com" in c["domain"]
            )
            return cookie_str, session_id


async def get_cookie_str(require_record_page=False, auto_launch=True):
    """
    通过 CDP 从 Chrome 浏览器获取腾讯会议的 Cookie 字符串。

    优先使用本地缓存的 Cookie（如果未过期且仍有效），
    避免每次运行都建立 CDP 连接触发浏览器确认弹窗。

    参数:
        require_record_page: 是否要求浏览器打开录制列表页面。
                             设为 False 则只要有任意 meeting.tencent.com 页面即可。
                             如果找不到，会自动通过 CDP 打开录制列表页。
        auto_launch: CDP 连接失败时是否自动尝试启动 Chrome。
                     默认 True。
    返回:
        cookie_str: 拼接好的 Cookie 字符串
    """
    # ── 优先尝试缓存 ──
    cached = _load_cookie_cache()
    if cached:
        if _validate_cookie(cached):
            print("✅ 使用缓存凭证（有效）")
            return cached
        else:
            print("⚠️  缓存凭证已失效，重新从浏览器获取...")

    # ── 缓存不可用，走 CDP ──
    ws_url = _get_ws_url(auto_launch=auto_launch)

    # WebSocket 连接（带重试，应对 Chrome 刚启动 handshake 还没就绪的情况）
    # Chrome 146+ 首次连接时会弹出确认对话框，需要用户点击允许
    for attempt in range(3):
        try:
            print(f"🔗 正在连接 Chrome CDP（如果浏览器弹出确认框，请点击「允许」）...")
            async with websockets.connect(
                ws_url, max_size=10**8, open_timeout=CDP_OPEN_TIMEOUT
            ) as ws:
                target = await _ensure_meeting_target(ws)
                cookie_str, _ = await _attach_and_get_cookies(ws, target)
                # 缓存 cookie 供后续使用
                _save_cookie_cache(cookie_str)
                return cookie_str

        except websockets.exceptions.InvalidURI:
            raise RuntimeError(
                f"❌ WebSocket URL 无效: {ws_url}\n"
                "DevToolsActivePort 文件可能已过期，请重启 Chrome。"
            )
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            if attempt < 2:
                print(f"⚠️  WebSocket 连接失败 (尝试 {attempt + 1}/3)，2秒后重试...")
                await asyncio.sleep(2)
            else:
                raise RuntimeError(
                    f"❌ 无法连接到 Chrome CDP: {e}\n"
                    "可能原因：\n"
                    "  - Chrome 已关闭\n"
                    "  - Chrome 的 CDP 确认对话框未点击「允许」\n"
                    "请重新打开 Chrome 后再试。"
                )


async def get_cdp_connection(auto_launch=True):
    """
    获取 CDP WebSocket 连接，并确保浏览器中存在腾讯会议页面。

    供需要直接操作 CDP（如 task_monitor）的脚本使用。

    参数:
        auto_launch: CDP 连接失败时是否自动启动 Chrome

    返回:
        (ws, target, session_id) 元组
        调用方需要自行管理 ws 的生命周期。
    """
    ws_url = _get_ws_url(auto_launch=auto_launch)

    for attempt in range(3):
        try:
            print(f"🔗 正在连接 Chrome CDP（如果浏览器弹出确认框，请点击「允许」）...")
            ws = await websockets.connect(
                ws_url, max_size=10**8, open_timeout=CDP_OPEN_TIMEOUT
            )
            target = await _ensure_meeting_target(ws)

            # attach
            await ws.send(json.dumps({
                "method": "Target.attachToTarget",
                "params": {"targetId": target["targetId"], "flatten": True},
                "id": 2
            }))
            session_id = None
            while True:
                m = json.loads(await ws.recv())
                if m.get("id") == 2:
                    session_id = m["result"]["sessionId"]
                    break
                if m.get("method") == "Target.attachedToTarget":
                    session_id = m["params"]["sessionId"]
                    break

            return ws, target, session_id

        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            if attempt < 2:
                print(f"⚠️  WebSocket 连接失败 (尝试 {attempt + 1}/3)，2秒后重试...")
                await asyncio.sleep(2)
            else:
                raise RuntimeError(
                    f"❌ 无法连接到 Chrome CDP: {e}\n"
                    "请重新打开 Chrome 后再试。"
                )


# ── 录制类型映射 ──────────────────────────────────────
RECORD_TYPE_MAP = {
    'cloud_record': '云端录制',
    'realtime_transcription': '实时转写',
    'fast_record': '快速录制',
    'user_upload': '用户上传',
    'voice_record': '语音录制',
}

RECORD_TYPE_FILTER = "fast_record|cloud_record|user_upload|realtime_transcription|voice_record"


def record_type_cn(record_type):
    """将英文 record_type 转为中文。"""
    return RECORD_TYPE_MAP.get(record_type, record_type)
