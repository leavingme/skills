# 百度网盘 MCP Skill (标准版)

## 简介

本 Skill 接入了百度网盘官方提供的 MCP Server，支持文件管理、搜索、上传、用户信息查询等核心功能。

## 功能列表

### 1. 基础信息查询
- `get_user_info`：获取用户基础信息（昵称、头像等）。
- `get_quota`：查看网盘总容量与剩余空间。

### 2. 文件列表与元数据
- `list_files`：列出目录下的文件，支持排序和分页。
- `get_file_metas`：获取特定文件的详细元数据。

### 3. 文件管理
- `mkdir`：创建新文件夹。
- `delete_files`：批量删除文件或文件夹。
- `copy` / `move` / `rename`：文件的复制、移动和重命名。

### 4. 搜索与上传
- `search_files`：在指定目录下搜索文件（支持递归）。
- `upload_file`：上传本地文件到网盘，支持大文件自动分片和断点续传。

## 🤖 给 Agent 的执行指南

作为 AI Assistant，你可以通过这些工具实现复杂的网盘管理任务。

### 🔑 Token 配置流程（必读）
- 在调用任何涉及网盘数据的工具前，如果提示未授权或缺少 Token，你需要主动帮用户配置：
  1. 请向用户发送这段信息：
     “配置缺失，请您点击此链接完成授权：[百度网盘个人体验授权](https://openapi.baidu.com/oauth/2.0/authorize?response_type=token&client_id=QHOuRXiepJBMjtk0esLhrPoNlQyYd0mF&redirect_uri=oob&scope=basic,netdisk)。点击授权后，请将最终跳转页面浏览器地址栏里的**完整 URL** 复制发给我。”
  2. 收到用户发来的完整 URL 后，调用 `configure_token` 工具，它会自动解析并持久化保存 Token。

### 典型工作流
1. **查看空间**：先通过 `get_quota` 确认存储空间。
2. **定位文件**：使用 `search_files` 或 `list_files` 找到目标。
3. **整理目录**：使用 `mkdir` 和 `move` 进行归档。

## 安装与配置

### 1. 获取 Access Token

`BAIDU_NETDISK_ACCESS_TOKEN` 是运行此 MCP Server 的必要环境变量。

#### 方法 A：个人用户（快速测试，限时体验）
如果你是个人用户且希望快速体验，可以按照以下步骤获取临时 Token：
1. **发起授权**：[点击此处发起授权请求](https://openapi.baidu.com/oauth/2.0/authorize?response_type=token&client_id=QHOuRXiepJBMjtk0esLhrPoNlQyYd0mF&redirect_uri=oob&scope=basic,netdisk)
2. **确认授权**：登录百度账号并点击“授权”。
3. **获取令牌**：在跳转后的页面 URL 中，找到 `access_token=` 之后的一串字符，复制即可。

> [!WARNING]
> 个人体验 Token 会不定期变更，且仅供测试。如需正式使用，请参考方法 B。

#### 方法 B：企业开发者（正式生产环境）
1. **注册**：在 [百度网盘开放平台](https://pan.baidu.com/union/welcome) 注册并完成实名认证。
2. **创建应用**：在控制台创建应用以获取 `AppKey`。
3. **获取令牌**：参考 [接入授权文档](https://pan.baidu.com/union/doc/ol0rsap9s) 通过 OAuth2.0 流程获取长效 Token。

### 2. 配置与启动

MCP Server 启动时会优先读取当前目录下的 `config.json` 以获取 Access Token。如果没有，则尝试从环境变量 `BAIDU_NETDISK_ACCESS_TOKEN` 读取，并自动覆盖保存到 `config.json` 中以便后续使用。

配置步骤（任选其一）：
- **方式一（直接修改文件）**：打开 `config.json`，将获取到的 Token 填入 `BAIDU_NETDISK_ACCESS_TOKEN` 字段。
- **方式二（环境变量）**：通过环境变量启动，服务会自动记录 Token。

```bash
uv --directory scripts/netdisk-mcp-server-stdio run netdisk.py
```

## 版本信息
- **版本**: 1.1.1 (标准版)
- **集成来源**: [百度网盘官方接入概要](https://pan.baidu.com/union/doc/fm9shpba6)
