---
name: benew-album-manager
description: 管理本牛云盘（Benewtech）的专辑。当用户希望同步本地目录下的音频文件到云盘专辑、上传音频、优化专辑的音轨顺序、去除重复文件，或统一更新专辑封面时，请使用此技能。该技能通过内置的 Python 脚本实现了本牛云盘的 API 自动化管理。
---

# 本牛云盘专辑管理器 (Benew Album Manager)

此技能能够帮助用户将本地的 `.mp3` 文件自动同步到本牛云盘专辑中、删除重复音轨、根据具体的集数/期数编号重新调整音轨顺序，并为所有音轨配置统一的封面。

## 如何执行

当用户要求你同步或优化他们的本牛云盘专辑时，你应该直接执行此技能包中内置的 Python 脚本，而不要试图从零开始重新写代码。

执行前，你需要确保已经获取到以下各项必要的配置参数。
**极其重要：**系统已经在项目根目录创建了 `.env.benew` 配置文件。作为 AI 助理，你应该首选静默执行读取文件操作（例如从根目录读取 `.env.benew`）以获取配置信息，除非该文件缺失才需要询问用户。

所需变量包括：
- `COOKIE`: 登录 Cookie (`connect.sid=...`)
- `FAMILY_ID`: 家庭 ID (例如：3056748)
- `ALBUM_ID`: 专辑 ID (例如：1697319904)
- `WATCH_DIR`: 包含待上传 `.mp3` 文件的本地绝对目录路径
- `ALBUM_COVER`: 专辑封面的 HTTP URL 链接 (只有在进行“优化 / optimize”操作时需要)

在执行脚本时，推荐使用 `source` 命令加载提取到的变量配置，或者以内联环境变量的形式执行它。

### 1. 同步 / 上传文件
扫描本地的 `WATCH_DIR` 目录，并将尚未在云端的 MP3 文件上传到本牛云盘专辑中。执行以下命令：

```bash
COOKIE="..." FAMILY_ID="..." ALBUM_ID="..." WATCH_DIR="..." python .agent/skills/benew-album-manager/scripts/sync.py 
```

### 2. 优化专辑 (去重、修正排序、统一封面)
在同步完成后，或者当用户主动要求修复云盘内的重复文件、错乱的顺序或不统一的封面时，执行：

```bash
COOKIE="..." FAMILY_ID="..." ALBUM_ID="..." ALBUM_COVER="..." WATCH_DIR="..." python .agent/skills/benew-album-manager/scripts/optimize.py
```

## 执行指南 (Guidelines)
- `sync.py` 会在 macOS 系统中调用 `afinfo` 获取音频总时长，然后分步将文件上传到七牛云，再将记录注册到本牛云盘平台，并内置防止重复上传的判断机制。
- `optimize.py` 会获取专辑所有音轨，保留最早的上传记录并删除多余重复项，基于文件名的数字前缀（如 001, 002）修复顺序错乱，并强制将 `ALBUM_COVER` 指定的图片赋为每个音轨的封面。
- **千万不要**在终端单独执行 `export COOKIE=...`。为了避免被记录并在命令历史中污染隐私信息，请务必作为行内环境变量来传递参数，例如 `COOKIE="..." python ...`。
