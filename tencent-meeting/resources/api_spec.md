- **发言人识别/转写接口**: `POST https://meeting.tencent.com/wemeet-tapi/v2/meetlog/record-detail/split-time-line-speaker`
- **内容导出/下载接口**: `GET https://meeting.tencent.com/wemeet-cloudrecording-webapi/v1/minutes/export_by_meeting`
  - **核心效果**: 通过该接口可直接获取转写内容的文本（TXT、PDF、DOCX等格式）或其云存储下载链接。
  - **重要参数**: `meeting_id`, `uniq_meeting_id`, `type` (导出格式), `id` (导出会话ID)。

## 2. 发言人识别接口 Payload 说明
抓取特定会议的发言人详情时，需要以下 Body：
```json
{
    "record_id": "录制ID",
    "meeting_id": "会议ID",
    "app_id": "1400115281",
    "user_id": "您的用户ID",
    "split_num": 8
}
```

## 3. 任务状态控制 API (生成中判定)
如果您需要判断“智能转写”或“智能总结”是否还在生成中，需要关注以下接口：

### A. 智能转写状态
- **Endpoint**: `POST https://meeting.tencent.com/wemeet-cloudrecording-webapi/v1/minutes/detail`
- **判定逻辑**: 
  - 当响应体顶层的 `code` 为 **`30003`** 时，表示“智能转写生成中…”。
  - 当 `code` 为 `0` 时，表示转写已完成。

### B. 智能总结/章节状态
- **Endpoint**: `POST https://meeting.tencent.com/wemeet-tapi/v2/meetlog/public/record-detail/query_smart_reddot_task`
- **判定逻辑**: 
  - 检查响应中的 `data.tasks` 数组。
  - `status: 2` 表示该任务正在生成中（Scene 2 通常为智能总结，Scene 3 为智能章节）。

## 4. 关键 Header 列表
| Header | 作用 | 备注 |
| :--- | :--- | :--- |
| `Cookie` | 身份凭证 | 必需包含 `we_meet_token` |
| `Web-Caller` | 接口来源 | 必须固定为 `my_meetings` |
| `Referer` | 来源页面 | 腾讯后端会校验来源 |
| `Content-Type` | 数据格式 | 固定为 `application/json` |

## 3. URL 动态参数 (Query Params)
每次请求建议携带最新的动态参数：
- `c_timestamp`: 当前毫秒级时间戳。
- `trace-id`: 32位 UUID。
- `c_nonce`: 随机字符串。

## 4. POST 报文体 (JSON Body)
```json
{
    "page_index": 1,
    "page_size": 25,
    "record_type_v4": "fast_record|cloud_record|user_upload|realtime_transcription|voice_record",
    "sort_by": "uni_record_id"
}
```

## 5. 开发建议
- **Session 有效期**：`we_meet_token` 的有效期通常较长（数天），但 `trace-id` 建议每次请求重新生成。
- **并发控制**：翻页请求建议加入 100-500ms 间隔，防止被腾讯网关限流。
