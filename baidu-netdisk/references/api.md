# main.py 命令参考

通过 `python scripts/main.py <操作> [参数]` 调用，所有操作均返回 JSON。

凭证从 `config.json` 读取（`BDUSS` / `STOKEN`），也可通过环境变量 `BAIDU_BDUSS` / `BAIDU_STOKEN` 传入。

---

## login

重新获取凭证，自动调起 CDP 脚本。

```bash
python scripts/main.py login
```

---

## list

列出指定目录的文件，返回文件列表。

```bash
python scripts/main.py list [path=/] [order=time]
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `path` | `/` | 网盘目录路径 |
| `order` | `time` | 排序方式：`time` / `name` / `size` |

返回示例：
```json
{
  "success": true,
  "count": 2,
  "files": [
    {"name": "电影", "path": "/电影", "size": "0.00 B", "is_dir": true, "modify_time": 1700000000, "fs_id": 123456}
  ]
}
```

---

## search

在网盘中按文件名关键字搜索。

```bash
python scripts/main.py search keyword=<关键字> [path=/]
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `keyword` | 必填 | 搜索关键字 |
| `path` | `/` | 搜索范围目录 |

---

## extract

列出分享链接根目录的文件列表，获取 `fs_id` 供后续精确转存使用。

```bash
python scripts/main.py extract share_url=<链接> [extract_code=<提取码>]
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `share_url` | 必填 | 分享链接 |
| `extract_code` | 空 | 提取码，无密码时省略 |

返回额外包含 `shareid`、`uk`、`sekey`，可用于后续 `transfer`。

---

## list_share

浏览分享链接中的指定子目录内容。

```bash
python scripts/main.py list_share share_url=<链接> [extract_code=<提取码>] [path=<子目录路径>]
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `share_url` | 必填 | 分享链接 |
| `extract_code` | 空 | 提取码 |
| `path` | 空（根目录） | 子目录完整绝对路径，如 `/资源/子目录` |

注意：`path` 必须是分享者网盘中的完整路径，从 `extract` 返回结果中获取。

---

## transfer

将分享文件转存到自己的网盘。

```bash
python scripts/main.py transfer share_url=<链接> [extract_code=<提取码>] [save_path=/我的资源] [fsids=<id>] [share_path=<子目录>]
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `share_url` | 必填 | 分享链接 |
| `extract_code` | 空 | 提取码 |
| `save_path` | `/我的资源` | 转存到自己网盘的目标路径 |
| `fsids` | 空（全部） | 逗号分隔的 fs_id，精确指定要转存的文件 |
| `share_path` | 空（根目录） | 转存分享链接中指定子目录的全部内容 |

典型工作流：
```bash
# 1. 先列出分享内容
python scripts/main.py extract share_url=https://pan.baidu.com/s/1xxxxx extract_code=abcd

# 2a. 转存全部
python scripts/main.py transfer share_url=https://pan.baidu.com/s/1xxxxx extract_code=abcd save_path=/电影

# 2b. 精确转存某个文件
python scripts/main.py transfer share_url=https://pan.baidu.com/s/1xxxxx fsids=710746060396824 save_path=/电影

# 2c. 转存某个子目录
python scripts/main.py transfer share_url=https://pan.baidu.com/s/1xxxxx share_path="/资源/2024" save_path=/电影
```

---

## mkdir

创建目录。

```bash
python scripts/main.py mkdir path=<目录路径>
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `path` | 必填 | 要创建的完整路径，如 `/我的资源/新目录` |

---

## delete

删除文件或目录（不可恢复，谨慎使用）。

```bash
python scripts/main.py delete path=<路径>
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `path` | 必填 | 要删除的文件或目录路径 |

---

## rename

重命名文件或目录。

```bash
python scripts/main.py rename path=<原路径> new_name=<新名称>
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `path` | 必填 | 原文件/目录完整路径 |
| `new_name` | 必填 | 新名称（仅文件名，不含路径） |

---

## move

移动文件或目录到另一个目录。

```bash
python scripts/main.py move path=<原路径> dest=<目标目录>
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| `path` | 必填 | 原文件/目录完整路径 |
| `dest` | 必填 | 目标目录路径 |
