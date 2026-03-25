"""
腾讯会议统一命令行工具。

整合录制列表、详情、导出、发言人识别、转写监控等功能，
CDP 连接只建立一次，cookie 在子命令间复用。

用法:
    python meeting.py list                          # 列出录制
    python meeting.py list --limit 5 --type cloud_record
    python meeting.py detail --keyword "周例会"      # 查看录制详情
    python meeting.py detail --index 1 --json
    python meeting.py export --keyword "周例会"      # 导出原始转写版纪要
    python meeting.py export --keyword "周例会" --smart  # 导出智能优化版纪要
    python meeting.py export --meeting_id X --uni_record_id Y --export_id Z
    python meeting.py speaker --record_id X --meeting_id Y  # 发言人时间轴
    python meeting.py monitor                       # 监控转写进度（CDP 长连接）
"""

import json
import asyncio
import argparse
import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_auth import (
    get_cookie_str, get_cdp_connection,
    _gen_params, _base_headers, record_type_cn,
    CORP_ID, UA, MEETING_DOMAIN, RECORD_TYPE_FILTER,
)


# ══════════════════════════════════════════════════════
#  子命令: list — 获取录制列表
# ══════════════════════════════════════════════════════

async def cmd_list(cookie_str, args):
    """获取录制列表。"""
    url = "https://meeting.tencent.com/wemeet-tapi/v2/meetlog/dashboard/my-record-list"
    headers = _base_headers(cookie_str)

    all_records = []
    for page_idx in range(1, 20):
        params = _gen_params()
        payload = {
            "begin_time": "0", "end_time": "0", "meeting_code": "",
            "page_index": page_idx, "page_size": 25,
            "aggregationFastRecording": 0,
            "cover_image_type": "meetlog_list_webp",
            "record_type_v4": RECORD_TYPE_FILTER,
            "sort_by": "uni_record_id", "record_scene": 1,
        }

        print(f"🚀 正在抓取第 {page_idx} 页...")
        try:
            resp = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
            if resp.status_code != 200:
                print(f"❌ HTTP {resp.status_code}")
                break
            data = resp.json()
            if data.get("code") != 0:
                print(f"❌ 第 {page_idx} 页 API 拒绝: {data}")
                break
            records = data.get("data", {}).get("records", []) or data.get("data", {}).get("list", [])
            if not records:
                break
            all_records.extend(records)
            if len(records) < 25:
                break
            if args.limit and len(all_records) >= args.limit:
                all_records = all_records[:args.limit]
                break
        except Exception as e:
            print(f"❌ 异常: {e}")
            break

    if args.record_type:
        all_records = [r for r in all_records if r.get('record_type') == args.record_type]

    if args.json:
        print(json.dumps(all_records, ensure_ascii=False, indent=2))
        return all_records

    print(f"\n🎉 成功！获取到 {len(all_records)} 条录制记录：")
    print("-" * 120)
    for i, r in enumerate(all_records, 1):
        dt = time.strftime('%Y-%m-%d %H:%M', time.localtime(int(r.get('start_time', 0)) / 1000))
        rtype = record_type_cn(r.get('record_type', ''))
        title = r.get('title') or r.get('meeting_name', '')
        
        # 处理时长 (毫秒 -> 分钟和秒)
        duration_ms = int(r.get('duration', 0))
        duration_sec = duration_ms // 1000
        mins = duration_sec // 60
        secs = duration_sec % 60
        duration_str = f"{mins}分{secs}秒" if mins > 0 else f"{secs}秒"

        print(f"{i:3}. [{dt}] {title} | 类型: {rtype} | 时长: {duration_str}")
        print(f"     record_id: {r.get('record_id', '')} | meeting_id: {r.get('meeting_id', '')} | uni_record_id: {r.get('uni_record_id', '')}")
    print("-" * 120)
    return all_records


# ══════════════════════════════════════════════════════
#  子命令: detail — 获取录制详情
# ══════════════════════════════════════════════════════

async def cmd_detail(cookie_str, args):
    """获取单条录制的详细信息。"""
    url = "https://meeting.tencent.com/wemeet-tapi/v2/meetlog/dashboard/my-record-list"
    headers = _base_headers(cookie_str)
    params = _gen_params()
    payload = {
        "begin_time": "0", "end_time": "0", "meeting_code": "",
        "page_index": 1, "page_size": 25,
        "aggregationFastRecording": 0,
        "cover_image_type": "meetlog_list_webp",
        "record_type_v4": RECORD_TYPE_FILTER,
        "sort_by": "uni_record_id", "record_scene": 1,
    }

    resp = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
    if resp.status_code != 200:
        print(f"❌ HTTP {resp.status_code}")
        return None
    data = resp.json()
    if data.get("code") != 0:
        print(f"❌ API 拒绝: {data}")
        return None

    records = data.get("data", {}).get("records", []) or data.get("data", {}).get("list", [])

    if args.record_type:
        records = [r for r in records if r.get('record_type') == args.record_type]
    if args.keyword:
        records = [r for r in records if args.keyword in (r.get('title') or r.get('meeting_name', ''))]
    if args.index is not None:
        if 1 <= args.index <= len(records):
            records = [records[args.index - 1]]
        else:
            print(f"❌ 序号 {args.index} 超出范围 (共 {len(records)} 条)")
            return None

    if not records:
        print("❌ 未找到匹配的录制。")
        return None

    target = records[0]

    if args.json:
        print(json.dumps(target, ensure_ascii=False, indent=2))
    else:
        dt = time.strftime('%Y-%m-%d %H:%M', time.localtime(int(target.get('start_time', 0)) / 1000))
        title = target.get('title') or target.get('meeting_name', '')
        print(f"\n🎯 找到目标录制: {title}")
        print(f"   时间:           {dt}")
        print(f"   类型:           {record_type_cn(target.get('record_type', ''))}")
        print(f"   record_id:      {target.get('record_id')}")
        print(f"   meeting_id:     {target.get('meeting_id')}")
        print(f"   uni_record_id:  {target.get('uni_record_id')}")
        print(f"   size:           {target.get('size', 0)} bytes")

    return target


# ══════════════════════════════════════════════════════
#  子命令: export — 导出会议纪要
# ══════════════════════════════════════════════════════

def _find_record(cookie_str, keyword, record_type=None):
    """通过关键词查找录制，返回第一条匹配结果。"""
    url = "https://meeting.tencent.com/wemeet-tapi/v2/meetlog/dashboard/my-record-list"
    headers = _base_headers(cookie_str)
    params = _gen_params()
    payload = {
        "begin_time": "0", "end_time": "0", "meeting_code": "",
        "page_index": 1, "page_size": 25,
        "aggregationFastRecording": 0,
        "cover_image_type": "meetlog_list_webp",
        "record_type_v4": RECORD_TYPE_FILTER,
        "sort_by": "uni_record_id", "record_scene": 1,
    }
    resp = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("code") != 0:
        return None
    records = data.get("data", {}).get("records", []) or data.get("data", {}).get("list", [])
    if record_type:
        records = [r for r in records if r.get('record_type') == record_type]
    if keyword:
        records = [r for r in records if keyword in (r.get('title') or r.get('meeting_name', ''))]
    return records[0] if records else None


def _do_export(cookie_str, meeting_id, uni_record_id, export_id,
               file_type="txt", output_dir=None, meeting_name=None,
               minutes_version="1"):
    """调用导出接口并下载文件。

    参数:
        minutes_version: "1" = 原始转写版, "0" = 智能优化版（AI 整理后的纪要）
    """
    url = "https://meeting.tencent.com/wemeet-cloudrecording-webapi/v1/minutes/export_by_meeting"
    params = _gen_params(
        meeting_id=meeting_id,
        uniq_meeting_id=uni_record_id,
        id=export_id,
        type=file_type,
        platform="Web",
        from_share="1",
        enter_from="share",
        page_source="record",
        minutes_version=minutes_version,
        lang="zh",
        # 以下为分享场景可选字段，留空即可
        recording_id="",
        tk="",
        pwd="",
        host="",
        activity_uid="",
    )
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Cookie": cookie_str,
        "Referer": "https://meeting.tencent.com/",
        "User-Agent": UA,
    }

    print(f"🚀 正在调用导出接口 (meeting_id={meeting_id}, format={file_type}, version={'智能优化版' if minutes_version == '0' else '原始转写版'})...")
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code}: {resp.text[:500]}")
            return None
        data = resp.json()
        if data.get("code") != 0:
            print(f"❌ API 返回错误: code={data.get('code')}, msg={data.get('msg', '')}")
            return None

        download_url = data.get("url") or (data.get("urls", [None])[0])
        if not download_url:
            print(f"⚠️ 接口未返回下载 URL: {data}")
            return None

        print("✅ 导出成功！正在下载...")
        save_dir = output_dir or os.path.expanduser("~/Downloads")
        os.makedirs(save_dir, exist_ok=True)

        date_str = time.strftime('%Y%m%d')
        name = meeting_name or f"meeting_{meeting_id}"
        safe_name = "".join(c for c in name if c not in r'\/:*?"<>|')
        version_tag = "_智能优化版" if minutes_version == "0" else ""
        filename = os.path.join(save_dir, f"{safe_name}_{date_str}{version_tag}_会议纪要.{file_type}")

        file_resp = requests.get(download_url, timeout=30)
        with open(filename, 'wb') as f:
            f.write(file_resp.content)

        print(f"✨ 下载完成！文件: {filename} ({len(file_resp.content)} 字节)")
        return filename

    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


async def cmd_export(cookie_str, args):
    """导出会议纪要（支持关键词查找或直接指定 ID）。"""
    # minutes_version: "0" = 智能优化版, "1" = 原始转写版
    minutes_version = "0" if args.smart else "1"

    if args.keyword:
        print(f"🔍 正在查找包含 \"{args.keyword}\" 的录制...")
        record = _find_record(cookie_str, args.keyword, args.record_type)
        if not record:
            print(f"❌ 未找到匹配 \"{args.keyword}\" 的录制。")
            return None
        title = record.get('title') or record.get('meeting_name', '')
        meeting_id = record.get('meeting_id') or record.get('meeting_info', {}).get('meeting_id', '')
        print(f"🎯 找到: {title} (record_id={record.get('record_id')}, meeting_id={meeting_id})")
        return _do_export(
            cookie_str,
            meeting_id=meeting_id,
            uni_record_id=record.get('uni_record_id'),
            export_id=record.get('record_id'),
            file_type=args.format,
            output_dir=args.output,
            meeting_name=title,
            minutes_version=minutes_version,
        )
    elif args.meeting_id and args.uni_record_id and args.export_id:
        return _do_export(
            cookie_str,
            meeting_id=args.meeting_id,
            uni_record_id=args.uni_record_id,
            export_id=args.export_id,
            file_type=args.format,
            output_dir=args.output,
            minutes_version=minutes_version,
        )
    else:
        print("❌ 请提供 --keyword 或完整的 --meeting_id + --uni_record_id + --export_id")
        return None


# ══════════════════════════════════════════════════════
#  子命令: speaker — 发言人时间轴
# ══════════════════════════════════════════════════════

async def cmd_speaker(cookie_str, args):
    """获取发言人识别和分段内容。"""
    url = "https://meeting.tencent.com/wemeet-tapi/v2/meetlog/record-detail/split-time-line-speaker"
    headers = _base_headers(cookie_str)
    params = _gen_params()
    payload = {
        "record_id": args.record_id,
        "app_id": CORP_ID,
        "meeting_id": args.meeting_id,
        "user_id": args.user_id,
        "split_num": 8,
    }

    print(f"🚀 正在获取发言人时间轴 (record_id={args.record_id})...")
    try:
        resp = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code}")
            return None
        data = resp.json()
        if data.get("code") != 0:
            print(f"❌ API 拒绝: {data}")
            return None

        lines = data.get("data", {}).get("list", [])

        if args.json:
            print(json.dumps(lines, ensure_ascii=False, indent=2))
        else:
            print(f"\n🎉 成功！获取到 {len(lines)} 条发言记录：")
            print("-" * 80)
            for item in lines[:20]:
                speaker = item.get("speaker_name", "未知")
                start_time = item.get("start_time_offset", 0)
                content = item.get("content", "")[:60]
                print(f"[{start_time}ms] {speaker}: {content}...")
            if len(lines) > 20:
                print(f"... (还有 {len(lines) - 20} 条，使用 --json 查看全部)")
            print("-" * 80)

        return lines

    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


# ══════════════════════════════════════════════════════
#  子命令: monitor — 监控转写进度（CDP 长连接）
# ══════════════════════════════════════════════════════

async def cmd_monitor(args):
    """通过 CDP 长连接监控智能转写/总结进度。

    注意：此命令不使用 cookie，而是直接通过 CDP 拦截网络请求。
    """
    print("📡 正在连接浏览器以监控『智能转写』状态...")
    ws, target, session_id = await get_cdp_connection()

    try:
        await ws.send(json.dumps({
            "sessionId": session_id,
            "method": "Network.enable",
            "id": 3
        }))

        print("💡 正在实时捕获状态接口数据（可手动刷新页面触发）...")
        timeout = 30
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))

                if m.get("method") == "Network.responseReceived":
                    url = m["params"]["response"]["url"]
                    request_id = m["params"]["requestId"]

                    if "minutes/detail" in url:
                        print(f"🎯 发现转写详情接口: {url}")
                        await ws.send(json.dumps({
                            "sessionId": session_id,
                            "method": "Network.getResponseBody",
                            "params": {"requestId": request_id},
                            "id": 101
                        }))

                    if "query_smart_reddot_task" in url:
                        print(f"🎯 发现 smart 任务状态接口: {url}")
                        await ws.send(json.dumps({
                            "sessionId": session_id,
                            "method": "Network.getResponseBody",
                            "params": {"requestId": request_id},
                            "id": 102
                        }))

                if m.get("id") == 101:
                    body = json.loads(m['result']['body'])
                    code = body.get("code")
                    status_text = "生成中 (Progressing)" if code == 30003 else "已完成 (Done)"
                    print(f"✅ 转写状态: {status_text} (Code: {code})")

                if m.get("id") == 102:
                    body = json.loads(m['result']['body'])
                    tasks = body.get("data", {}).get("tasks", [])
                    print("✅ AI 任务状态:")
                    for t in tasks:
                        scene = t.get("scene")
                        status = t.get("status")
                        scene_name = {2: "智能总结", 3: "智能章节"}.get(scene, f"场景{scene}")
                        status_name = "生成中" if status == 2 else "已完成"
                        print(f"   - {scene_name}: {status_name} (Status: {status})")

            except asyncio.TimeoutError:
                continue
            except Exception:
                pass
    finally:
        await ws.close()


# ══════════════════════════════════════════════════════
#  主入口：解析子命令，统一获取 cookie
# ══════════════════════════════════════════════════════

def build_parser():
    parser = argparse.ArgumentParser(
        description="腾讯会议统一命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python meeting.py list --limit 5
  python meeting.py detail --keyword "周例会"
  python meeting.py export --keyword "周例会" --format txt
  python meeting.py export --keyword "周例会" --smart          # 导出智能优化版
  python meeting.py speaker --record_id XXX --meeting_id YYY
  python meeting.py monitor
        """,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # list
    p_list = sub.add_parser("list", help="获取录制列表")
    p_list.add_argument("--limit", type=int, help="限制返回条数")
    p_list.add_argument("--type", dest="record_type", help="过滤录制类型")
    p_list.add_argument("--json", action="store_true", help="输出 JSON 格式")

    # detail
    p_detail = sub.add_parser("detail", help="获取录制详情")
    p_detail.add_argument("--keyword", help="按会议名称关键词搜索")
    p_detail.add_argument("--index", type=int, help="按序号选取 (1-based)")
    p_detail.add_argument("--type", dest="record_type", help="过滤录制类型")
    p_detail.add_argument("--json", action="store_true", help="输出 JSON")

    # export
    p_export = sub.add_parser("export", help="导出会议纪要")
    p_export.add_argument("--keyword", help="按关键词查找并导出")
    p_export.add_argument("--meeting_id", help="会议 ID")
    p_export.add_argument("--uni_record_id", help="统一录制 ID")
    p_export.add_argument("--export_id", help="导出 ID (record_id)")
    p_export.add_argument("--type", dest="record_type", help="录制类型过滤")
    p_export.add_argument("--format", default="txt", help="导出格式: txt/pdf/docx")
    p_export.add_argument("--output", help="输出目录 (默认 ~/Downloads)")
    p_export.add_argument("--smart", action="store_true",
                          help="导出智能优化版纪要（AI 整理后），默认导出原始转写版")

    # speaker
    p_speaker = sub.add_parser("speaker", help="获取发言人时间轴")
    p_speaker.add_argument("--record_id", required=True, help="录制 ID")
    p_speaker.add_argument("--meeting_id", required=True, help="会议 ID")
    p_speaker.add_argument("--user_id", default="milochen", help="用户 ID")
    p_speaker.add_argument("--json", action="store_true", help="输出 JSON")

    # monitor
    sub.add_parser("monitor", help="监控智能转写/总结进度")

    return parser


async def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # monitor 命令特殊处理：直接走 CDP 长连接，不需要 cookie
    if args.command == "monitor":
        await cmd_monitor(args)
        return

    # 其他命令：统一获取一次 cookie，复用给子命令
    print("📡 正在从浏览器同步凭证...")
    cookie_str = await get_cookie_str(require_record_page=True)
    print("✅ 凭证获取成功\n")

    if args.command == "list":
        await cmd_list(cookie_str, args)
    elif args.command == "detail":
        await cmd_detail(cookie_str, args)
    elif args.command == "export":
        await cmd_export(cookie_str, args)
    elif args.command == "speaker":
        await cmd_speaker(cookie_str, args)


if __name__ == "__main__":
    asyncio.run(main())
