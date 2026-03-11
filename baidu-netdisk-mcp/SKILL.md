# 百度网盘 MCP Skill

## 简介

本 Skill 接入了百度网盘官方提供的 MCP Server (Stdio 模式)，支持通过官方 API 进行文件管理、上传和下载。

## 功能特性

- 📁 **文件列表** - 查看指定目录的文件。
- 🔍 **文件搜索** - 搜索网盘内的文件。
- ⬆️ **文件上传** - 支持将本地文件上传到网盘。
- ⬇️ **文件获取** - 获取文件下载地址或元数据。

## 🤖 给 Agent 的执行指南

作为 AI Assistant，当你需要执行百度网盘操作时，可以使用 `baidu-netdisk-mcp` 提供的工具。

### 核心工具说明
- `list`：列出目录内容。
- `search`：搜索文件。
- `upload`：上传本地文件。
- `get_file_metas`：获取文件详细信息。

### 启动方式
该 MCP Server 使用 `uv` 运行。配置文件位于：
`/Users/leavingme/GitHub/skills/baidu-netdisk-mcp/config.json`

运行时需要设置环境变量 `BAIDU_NETDISK_ACCESS_TOKEN`。

## 安装与配置

### 1. 依赖环境
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)

### 2. 配置
在 `config.json` 中填入你的 `BAIDU_NETDISK_ACCESS_TOKEN`。

## 使用方法 (Stdio 模式)

你可以直接运行脚本进行测试：
```bash
export BAIDU_NETDISK_ACCESS_TOKEN="你的Token"
cd scripts/netdisk-mcp-server-stdio
uv run netdisk.py
```

## 版本信息
- **版本**: 1.0.0
- **集成来源**: [百度网盘官方 MCP SDK](https://pan.baidu.com/union/doc/Cm9si7mfw)
