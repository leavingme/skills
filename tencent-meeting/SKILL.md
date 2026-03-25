---
name: tencent-meeting
description: 腾讯会议自动化助手。支持获取录制列表、查看录制详情、监控转写进度、识别发言人时间轴以及导出下载转写文本。当用户需要查看腾讯会议录制、下载会议纪要、获取转写内容时，使用此 skill。
---

# 腾讯会议自动化 Skill

该 Skill 通过 Chrome DevTools Protocol (CDP) 从浏览器同步登录凭证，实现对腾讯会议录制资产的自动化管理。无需手动复制 Cookie 或配置 API 密钥。

## 前置条件

- Chrome 浏览器 **146 及以上版本**（`chrome://settings/help` 查看），已登录腾讯会议
- 已安装 Python 依赖: `pip install requests websockets`

### Chrome CDP 连接

脚本通过 Chrome DevTools Protocol (CDP) 获取登录凭证。Chrome 146+ 默认生成 `DevToolsActivePort` 文件，脚本自动读取该文件进行连接。

**连接策略**（按优先级）：

1. **DevToolsActivePort 文件**（Chrome 默认生成，多数情况下直接可用）
2. **自动启动**（Chrome 未运行时，脚本会自动打开 Chrome 并等待就绪）

**⚠️ 首次连接注意**: Chrome 146+ 首次通过 CDP 连接时，浏览器会弹出确认对话框，**需要用户点击「允许」** 才能完成连接。脚本已设置 30 秒超时等待用户确认。

**如果浏览器中没有腾讯会议页面**: 脚本会自动通过 CDP 打开录制列表页（`https://meeting.tencent.com/user-center/meeting-record`），无需用户手动操作。

**如果自动连接失败**，请手动操作：

1. 完全关闭 Chrome（Cmd+Q）
2. 重新打开 Chrome
3. 确认已登录腾讯会议
4. 重新运行脚本

## 脚本说明 (scripts/)

| 脚本 | 功能 | 说明 |
|------|------|------|
| `meeting.py` | **统一入口** — 所有业务功能通过子命令调用 | CDP 连接只建立一次，cookie 在子命令间复用 |
| `cdp_auth.py` | **公共模块** — CDP 凭证同步、通用请求参数生成 | 无需直接调用 |

## 使用流程

所有功能通过 `meeting.py` 的子命令调用，CDP 连接只建立一次：

### 流程 A: 查看录制列表

```bash
python scripts/meeting.py list
python scripts/meeting.py list --limit 5 --type cloud_record
python scripts/meeting.py list --json
```

输出包含每条录制的**时间、名称、类型（云端录制/实时转写/...）、record_id、meeting_id、uni_record_id**。

### 流程 B: 下载会议纪要

**快捷方式** — 按关键词一键导出：
```bash
python scripts/meeting.py export --keyword "周例会"
python scripts/meeting.py export --keyword "周例会" --type cloud_record --format txt
```

**导出智能优化版纪要**（AI 整理后的版本，更适合阅读）：
```bash
python scripts/meeting.py export --keyword "周例会" --smart
python scripts/meeting.py export --keyword "周例会" --smart --format txt
```

> 说明：默认导出原始转写版（`minutes_version=1`），加 `--smart` 后导出智能优化版（`minutes_version=0`），即腾讯会议 AI 自动整理后的会议纪要。智能优化版的文件名中会包含 `_智能优化版` 标识。

**手动指定 ID**（适用于已知参数的情况）：
```bash
python scripts/meeting.py export --meeting_id XXX --uni_record_id YYY --export_id ZZZ --format txt
python scripts/meeting.py export --meeting_id XXX --uni_record_id YYY --export_id ZZZ --smart
```

文件默认保存到 `~/Downloads`，可通过 `--output` 指定目录。

### 流程 C: 获取录制详情

当需要获取某条录制的完整参数（用于其他操作）时：
```bash
python scripts/meeting.py detail --keyword "周例会" --type cloud_record
python scripts/meeting.py detail --index 1 --json
```

### 流程 D: 获取发言人内容

需要先通过流程 A 或 C 获取 `record_id` 和 `meeting_id`：
```bash
python scripts/meeting.py speaker --record_id XXX --meeting_id YYY
```

### 流程 E: 监控转写进度

刚结束的会议可能转写尚未完成：
```bash
python scripts/meeting.py monitor
```
运行后手动刷新浏览器页面，脚本会自动捕获状态接口数据。

> **注意**: `monitor` 命令使用 CDP 长连接直接拦截浏览器网络请求，不走 cookie 模式。

## 录制类型说明

同一场会议可能生成多条录制资源，通过 `record_type` 字段区分：

| record_type | 中文名 | 说明 |
|-------------|--------|------|
| `cloud_record` | 云端录制 | 视频/音频录制文件，体积大，可回放 |
| `realtime_transcription` | 实时转写 | 会议文字记录，体积小 |
| `fast_record` | 快速录制 | 快速录制文件 |
| `user_upload` | 用户上传 | 用户手动上传的文件 |
| `voice_record` | 语音录制 | 纯语音录制 |

在展示录制列表时，始终显示 `record_type` 对应的中文名称，方便用户区分同一场会议的不同资源。

## 注意事项

- **凭证时效**: 依赖浏览器的登录状态。浏览器退出登录则脚本失效。
- **签名参数**: `c_timestamp`、`trace-id`、`c_nonce` 每次请求自动生成，无需手动管理。
- **并发控制**: 翻页请求间有自然延迟，无需额外控制。
- **CDP 确认**: Chrome 146+ 首次 CDP 连接会弹出确认框，后续连接不再弹出。
