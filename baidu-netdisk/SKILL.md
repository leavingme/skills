---
name: baidu-netdisk-go
description: |
  百度网盘操作 skill，结合 BaiduPCS-Go 命令行工具和 Python API 脚本，覆盖完整的网盘操作能力。管理类操作（列目录、搜索、浏览分享链接、转存、重命名、移动、删除）通过 scripts/main.py 执行，返回结构化 JSON，Agent 友好；文件传输类操作（上传、下载、离线下载）通过 BaiduPCS-Go 命令执行。当用户需要操作百度网盘、转存分享链接、上传下载文件、管理网盘文件时请使用此 skill。
---

# 百度网盘 Skill 使用指南

本 skill 结合两种工具：**`main.py`**（Python API，结构化 JSON 输出）和 **BaiduPCS-Go**（命令行客户端，支持文件传输）。

## 能力分工

优先按以下原则选择工具：

| 操作 | 使用工具 | 原因 |
|---|---|---|
| 列目录、搜索文件 | `main.py` | 返回结构化 JSON，便于解析和后续处理 |
| 浏览分享链接、转存 | `main.py` | 支持指定保存路径、精确转存、子目录转存 |
| 文件管理（创建/删除/重命名/移动） | `main.py` | 结构化结果便于判断成败 |
| 下载文件到本地 | `BaiduPCS-Go` | 多线程、断点续传 |
| 上传文件到网盘 | `BaiduPCS-Go` | 大文件分片上传 |
| 离线下载、回收站、分享、多账号 | `BaiduPCS-Go` | 专属功能，`main.py` 不支持 |

---

## 第一步：获取凭证

如果尚未安装 BaiduPCS-Go，请先到 https://github.com/qjfoidnh/BaiduPCS-Go/releases/ 下载对应平台的可执行文件。

**不安装 BaiduPCS-Go 也可以完成**（通过 `main.py`）：列目录、搜索文件、浏览分享链接、转存、创建目录、删除、重命名、移动。

**必须安装 BaiduPCS-Go 才能完成**：下载文件到本地、上传文件、离线下载、回收站管理、创建分享链接、多账号切换。

两个工具使用不同的凭证存储方式，首次使用需分别配置。

### main.py 凭证（config.json）

运行 CDP 脚本，自动启动 Chrome 并在登录后抓取 BDUSS / STOKEN，写入 `config.json`：

```bash
python scripts/get_cookie_cdp.py
```

脚本会自动检测 Chrome → 打开百度网盘页面 → 等待登录 → 保存凭证。

手动获取：浏览器打开百度网盘 → 开发者工具 → Application → Cookies，找 `BDUSS` 和 `STOKEN`（STOKEN 应包含大写字母，否则可能拿错了）。

### BaiduPCS-Go 凭证（独立配置）

BaiduPCS-Go 有自己的配置系统，需单独登录：

```bash
# 推荐：用 BDUSS + STOKEN 登录
BaiduPCS-Go login -bduss=<BDUSS> -stoken=<STOKEN>

# 或用完整 Cookies 登录
BaiduPCS-Go login -cookies="<Cookies>"
```

多账号管理：
```bash
BaiduPCS-Go who          # 当前账号
BaiduPCS-Go loglist      # 所有已登录账号
BaiduPCS-Go su <uid>     # 切换账号
BaiduPCS-Go logout       # 退出当前账号
```

---

## 列出文件 / 搜索

优先用 `main.py`（结构化 JSON，便于后续处理）：

```bash
python scripts/main.py list [path=/] [order=time|name|size]
python scripts/main.py search keyword=<关键字> [path=/]
```

需要交互式浏览或查看树形结构时用 BaiduPCS-Go：

```bash
BaiduPCS-Go ls [目录] [-asc|-desc] [-time|-name|-size]
BaiduPCS-Go tree [目录]        # 树形图
BaiduPCS-Go meta <路径>        # 文件元信息
BaiduPCS-Go quota              # 网盘配额
BaiduPCS-Go cd <目录>          # 切换工作目录（交互模式）
BaiduPCS-Go pwd                # 当前工作目录
```

---

## 转存分享链接

推荐工作流：先浏览分享内容，再按需转存。

```bash
# 1. 预览分享链接根目录（获取文件列表和 fs_id）
python scripts/main.py extract share_url=<链接> [extract_code=<提取码>]

# 2. 浏览子目录（path 需使用 extract 返回的完整路径）
python scripts/main.py list_share share_url=<链接> [extract_code=<提取码>] [path=<子目录路径>]

# 3a. 转存全部到指定路径
python scripts/main.py transfer share_url=<链接> [extract_code=<提取码>] save_path=/我的资源

# 3b. 精确转存指定文件（fsids 来自 extract/list_share 结果）
python scripts/main.py transfer share_url=<链接> fsids=<fs_id1,fs_id2> save_path=/我的资源

# 3c. 转存指定子目录的全部内容
python scripts/main.py transfer share_url=<链接> share_path="/资源/子目录" save_path=/我的资源
```

BaiduPCS-Go 转存（只能存到当前工作目录）：
```bash
BaiduPCS-Go transfer <分享链接> [提取码]
```

---

## 文件管理

用 `main.py`（返回结构化 JSON）：

```bash
python scripts/main.py mkdir path=<目录路径>
python scripts/main.py delete path=<路径>
python scripts/main.py rename path=<原路径> new_name=<新名称>
python scripts/main.py move path=<原路径> dest=<目标目录>
```

BaiduPCS-Go 独有（复制）：
```bash
BaiduPCS-Go cp <源路径> <目标路径>
BaiduPCS-Go rm <路径>           # 删除（进回收站）
BaiduPCS-Go mv <源路径> <目标>  # 移动/重命名
```

---

## 文件下载

```bash
BaiduPCS-Go d <网盘路径> [--saveto <本地目录>] [-p <线程数>] [--ow]
```

**线程数建议**：普通用户 `max_parallel=1`，调大容易触发限速（持续数小时至数天）；SVIP 建议 10~20。

---

## 文件上传

```bash
BaiduPCS-Go u <本地路径> ... <网盘目标目录> [--norapid] [--policy skip|overwrite|rsync]
```

- `--norapid` — 跳过秒传
- `--policy rsync` — 只覆盖大小不同的同名文件

---

## 离线下载

支持 http/https/ftp/电驴/磁力链：

```bash
BaiduPCS-Go offlinedl add -path=<保存路径> <资源地址> ...
BaiduPCS-Go offlinedl list
BaiduPCS-Go offlinedl cancel <任务ID>
BaiduPCS-Go offlinedl delete -all   # 清空，谨慎！
```

---

## 分享 / 回收站

```bash
# 分享
BaiduPCS-Go share set <路径> ...    # 创建分享
BaiduPCS-Go share list              # 查看已分享
BaiduPCS-Go share cancel <shareid> # 取消分享

# 回收站
BaiduPCS-Go recycle list
BaiduPCS-Go recycle restore <fs_id>
BaiduPCS-Go recycle delete -all    # 清空，谨慎！
```

---

## 配置 / 常见问题

```bash
BaiduPCS-Go config set -savedir <目录>       # 设置下载目录
BaiduPCS-Go config set -max_parallel <数量>  # 下载并发数
BaiduPCS-Go config reset                     # 恢复默认
```

配置文件：Windows `%APPDATA%\BaiduPCS-Go`，Linux/macOS `$HOME/.config/BaiduPCS-Go`

- **上传异常**：尝试修改 `pcs_addr`，可选 `c.pcs.baidu.com`、`c2~c5.pcs.baidu.com`
- **输出乱码**：检查终端编码是否为 UTF-8

---

详细参考：
- `references/api.md` — `main.py` 所有操作和参数说明
- `references/commands.md` — BaiduPCS-Go 完整命令参考
