# Anthropic Skills 管理最佳实践总结

本建议旨在总结 Anthropic 官方推荐的技能（Skills）管理模式，以提升 AI Agent 对技能的发现效率、执行准确性，并优化 Token 使用量。

---

## 1. 核心理念：由内而外的驱动

Anthropic 模式的核心在于将技能视为一个 **“可即插即用的微服务”**。每个技能文件夹都是自包含的，且拥有明确的元数据描述。

### 核心原则：
*   **自包含 (Self-contained)**：一个文件夹就是一个技能，包含代码、配置和说明，不依赖外部路径。
*   **元数据优先 (Metadata First)**：Agent 在扫描仓库时，首先读取轻量级的元数据，而不是全量代码。

---

## 2. 设计规范

### 2.1 YAML Frontmatter（发现效率的关键）
每个技能的 `SKILL.md` 顶部必须包含一个 YAML 区块。

```yaml
---
name: baidu-netdisk-mcp
description: 专门用于处理百度网盘的文件列表、批量移动、重命名及分享链接生成的工具，基于官方 MCP 协议。
labels: [storage, cloud-drive, file-management]
---
```
*   **作用**：当用户提问“帮我整理网盘”时，Agent 通过扫描所有文件夹下的 `description` 字段即可快速锁定目标，而无需读取所有文件夹里的内容，极大地降低了 Token 消耗。

### 2.2 人机分离：SKILL.md vs README.md
*   **README.md (人读)**：放在仓库根目录，包含展示图、安装命令、项目背景等，帮助开发者理解。
*   **SKILL.md (机读)**：放在技能子目录，包含 YAML 元数据和详细的 **SOP (标准作业程序)**。它是写给 Agent 的“操作手册”。

### 2.3 规范化的文件结构
```text
skills/
├── [skill-name]/
│   ├── SKILL.md          # 技能定义与 Agent 指令 (必选)
│   ├── skill.json        # 依赖与环境配置 (可选)
│   ├── scripts/          # 核心逻辑脚本
│   └── references/       # 补充性文档（Agent 需要深度理解时才会访问）
```

---

## 3. 指令编写技巧 (SOP)

在 `SKILL.md` 的 Markdown 部分，应包含以下内容：

1.  **场景触发**：明确告诉 Agent 在什么情况下应该使用本技能。
2.  **配置引导**：如果缺少凭证（如 Token），Agent 应如何引导用户提供（例如提供授权链接并接收跳转 URL）。
3.  **约束与边界**：明确告诉 Agent 哪些操作是危险的（如批量删除）以及如何规避。
4.  **工作流示例**：给 Agent 提供 2-3 个典型的工具调用序列。

---

## 4. 针对 `leavingme/skills` 的改进方案

1.  **路径固化**：彻底告别本地开发目录与仓库目录的分离。直接在 `skills/` 下进行开发，确保 `file://` 路径在 IDE 和 Agent 视图中完全一致。
2.  **元数据升级**：逐步为所有子技能添加 YAML Frontmatter。
3.  **自动化维护**：在根目录建立扫描脚本，自动根据子目录的 `SKILL.md` 生成总的 `README.md`。
4.  **Token 持久化中间件**：参考本项目中的 `configure_token` 模式，为所有需要 Access Token 的技能建立统一的“配置-保存-读取”交互流。

---
*总结：好的 Skill 管理不仅是代码的整理，更是对 Agent “认知与发现逻辑”的优化。*
