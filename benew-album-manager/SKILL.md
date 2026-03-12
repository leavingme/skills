---
name: benew-album-manager
description: 管理本牛云盘（Benewtech）的专辑。支持同步本地音频、上传文件、优化音轨顺序、自动去重及统一封面。
---

# 本牛云盘全功能助手 (Benew Tool)

此技能通过一个统一的脚本 `scripts/benew_tool.py` 提供本牛云盘的自动化管理能力。

## 核心流程 (Execution Flow)

当用户要求同步、优化或管理专辑时，请遵循以下标准流程：

### 1. 凭证准备 (Auth)
首先检查并获取必要的 Cookie (`connect.sid`) 和 `FAMILY_ID`。
**极其重要：** 优先读取工作区根目录下的 `.env.benew` 文件。如果凭证缺失或过期，立即运行抓取脚本（系统将自动打开 Chrome 提取凭证）：

```bash
python "scripts/get_cookie_cdp.py"
```

### 2. 目标确认 (Discovery)
如果用户没有提供具体的 `ALBUM_ID`，请按以下顺序引导用户：
1. **查看文件夹**: `python "scripts/benew_tool.py" folder list`
2. **选择/创建专辑**: 
   * 列出专辑: `python "scripts/benew_tool.py" album list <folder_id>`
   * 创建专辑: `python "scripts/benew_tool.py" album create <folder_id> <name>`

### 3. 执行任务 (Commands)

#### 文件夹与专辑管理
```bash
# 列出根目录文件夹
python "scripts/benew_tool.py" folder list

# 新建文件夹
python "scripts/benew_tool.py" folder create <name>

# 列出文件夹下的专辑
python "scripts/benew_tool.py" album list <folder_id>

# 新建专辑
python "scripts/benew_tool.py" album create <folder_id> <name>
```

#### 音轨文件管理 (Tracks)
```bash
# 列出专辑内的音频列表
python "scripts/benew_tool.py" track list <album_id>

# 更新音频信息 (如改名)
python "scripts/benew_tool.py" track update <track_id> <new_name>

# 批量删除音轨
python "scripts/benew_tool.py" track delete <track_id>
```

#### 同步与优化 (Core Tasks)
*   **同步**: 将本地 `WATCH_DIR` 目录中的 MP3 增量上传到云端的 `ALBUM_ID`。
*   **优化**: 自动修正排序（基于文件名编号）、去重、统一封面。

```bash
# 执行同步 (会自动触发优化)
python "scripts/benew_tool.py" sync <album_id> <local_dir_path>

# 单独执行优化
python "scripts/benew_tool.py" optimize <album_id>
```

## 执行指南 (Guidelines)
- **静默执行**: 除非绝对必要（如需要用户选择文件夹），否则应尽可能利用缓存的 `.env.benew` 自动完成任务。
- **环境要求**: `sync` 功能依赖 macOS 的 `afinfo` 获取采样率和时长。
- **防止重复**: 所有的上传操作都内置了基于名称和编号的去重判断，无需担心重复上传。
