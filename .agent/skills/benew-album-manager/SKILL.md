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

如果缺失关键参数（尤其是 `COOKIE` 或 `FAMILY_ID`），**请绝对不要再去询问用户或让用户提供，用户不需要关心这些底层参数。**你应该自行排障：

1. 立即依靠所处运行环境的命令行调用为你写好的自动提权抓取脚本（这无须打扰用户，它将尝试直接从已运行的用户 Chrome 提取全部凭证）。**注意：请使用相对于本 `SKILL.md` 的绝对路径来拼接出 `scripts/get_cookie_cdp.py` 的位置后再执行，以适配任何所在的运行工作区环境！** 例如：
   ```bash
   python "/绝对路径/.../scripts/get_cookie_cdp.py"
   ```
2. **极速排障：** 如果提示没有 `websocket-client` 模块报错，请立刻在终端为用户执行 `pip install websocket-client` 静默安装，完成后再次运行该脚本！如果是 CDP 报错，脚本自身会进行针对 Playwright `get_cookie.py` 的自动降级弹窗提取，你只需等待其执行完毕。
3. 当脚本执行成功结束后，你应再次解析已被它更新过的 `.env.benew` 文件以捕获缺失的 `connect.sid` 和 `FAMILY_ID`，然后继续衔接你原来本该做的云盘同步/优化脚本。


所需变量包括：
- `COOKIE`: 登录 Cookie (`connect.sid=...`)
- `FAMILY_ID`: 家庭 ID (例如：3056748)
- `ALBUM_ID`: 专辑 ID (例如：1697319904，**极其重要：如果用户给你的只是一串形如 `https://pan.benewtech.cn/disk/cloudTrack/1697319904` 的网址，那么最后的数字 `1697319904` 就是你要提取的 ALBUM_ID**！)
- `WATCH_DIR`: 包含待上传 `.mp3` 文件的本地绝对目录路径
- `ALBUM_COVER`: (可选) 专辑封面的 HTTP URL 链接。如果不提供，脚本将自动尝试从云端抓取该专辑的默认封面。

**自动获取与交互式配置引导流程 (Interactive Configuration Flow)：**
- **第一步：凭证检查。** 如果缺失 `FAMILY_ID` 或 `COOKIE`，优先执行 `scripts/get_cookie_cdp.py` 自动化抓取（见上文）。
- **第二步：目标确认 (Interactive Discovery)。** 如果缺失 `ALBUM_ID` 或用户未明确上传到哪个专辑，**请执行以下交互流程**：
  1. 调用 `scripts/cloud_manager.py list_folders` 获取根目录列表。
  2. 将文件夹列表展示给用户，并询问：“您想将音频上传到哪个文件夹？（或输入文件夹名称，我为您新建一个）”。
  3. 用户确认文件夹 ID 后，调用 `scripts/cloud_manager.py list_albums <folder_id>` 获取该目录下的专辑。
  4. 展示专辑列表，询问用户选择现有专辑或输入新专辑名称进行创建。
  5. 最终确认 `ALBUM_ID` 后，再进行后续的同步操作。
- **第三步：永久保存用户的配置项（非常关键）。** 无论是通过交互获取的还是用户直接提供的 `ALBUM_ID` 或 `WATCH_DIR`，你作为 AI 必须主动使用文件读取与更新能力，将这些参数更新或追加保存到 `.env.benew` 配置文件中！这样下次运行时用户就不必再重复提供了。

在执行脚本时，推荐读取并解析这个 `.env.benew` 文件的结果，以内联环境变量的形式执行任务脚本（例如 `COOKIE="..." FAMILY_ID="..." ... python sync.py`）。


### 1. 云端元数据管理 (文件夹 & 专辑 CRUD)
当用户要求列出文件夹、新建目录、或在特定文件夹下创建新专辑时，使用 `cloud_manager.py`。

```bash
# 列出根目录文件夹
python "scripts/cloud_manager.py" list_folders

# 列出文件夹下的专辑
python "scripts/cloud_manager.py" list_albums <folder_id>

# 新建文件夹
python "scripts/cloud_manager.py" create_folder <name>

# 重命名文件夹
python "scripts/cloud_manager.py" rename_folder <folder_id> <new_name>

# 删除文件夹
python "scripts/cloud_manager.py" delete_folder <folder_id>

# 在文件夹下新建专辑
python "scripts/cloud_manager.py" create_album <folder_id> <name>

# 重命名专辑
python "scripts/cloud_manager.py" update_album <album_id> <new_name>

# 删除专辑
python "scripts/cloud_manager.py" delete_album <folder_id> <album_id>
```

### 2. 同步 / 上传文件
扫描本地的 `WATCH_DIR` 目录，并将尚未在云端的 MP3 文件上传到本牛云盘专辑中。执行以下命令（注意将脚本路径替换为推导出的真实绝对路径）：

```bash
COOKIE="..." FAMILY_ID="..." ALBUM_ID="..." WATCH_DIR="..." python "/绝对路径/.../scripts/sync.py" 
```

### 3. 优化专辑 (去重、修正排序、统一封面)
在同步完成后，或者当用户主动要求修复云盘内的重复文件、错乱的顺序或不统一的封面时，执行（注意将脚本路径替换为推导出的真实绝对路径）：

```bash
COOKIE="..." FAMILY_ID="..." ALBUM_ID="..." ALBUM_COVER="..." WATCH_DIR="..." python "/绝对路径/.../scripts/optimize.py"
```

## 执行指南 (Guidelines)
- **文件夹管理**: 所有的文件夹相关操作都应该在 `scripts/cloud_manager.py` 中进行逻辑封闭。
- `sync.py` 会在 macOS 系统中调用 `afinfo` 获取音频总时长，然后分步将文件上传到七牛云，再将记录注册到本牛云盘平台，并内置防止重复上传的判断机制。
- `optimize.py` 会获取专辑所有音轨，保留最早的上传记录并删除多余重复项，基于文件名的数字前缀（如 001, 002）修复顺序错乱，并强制将 `ALBUM_COVER` 指定的图片赋为每个音轨的封面。
- **千万不要**在终端单独执行 `export COOKIE=...`。为了避免被记录并在命令历史中污染隐私信息，请务必作为行内环境变量来传递参数，例如 `COOKIE="..." python ...`。
