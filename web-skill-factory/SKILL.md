---
name: web-skill-factory
description: Web 服务技能工厂。当用户需要为一个新的 Web 网站或服务创建 AI 技能时，请使用本技能。它提供了一套标准化的“探测-提取-实现”流程，并附带基于 CDP 的 Cookie 抓取和 API 客户端模板。它能确保生成的技能具有自动处理登录凭证、稳定性高且符合最佳实践。
---

# Web 技能工厂 (Web Skill Factory)

本技能旨在为 AI Agent 提供一套工业级的流程，用于快速、高质量地为任何 Web 服务构建自定义技能（Skills）。

## 核心流程 (Methodology)

当你接收到“为 X 网站创建一个技能”的任务时，请严格遵循以下步骤：

### 第一步：探测与观察 (Probing & Observation)
不要盲目猜测 API。请先启动浏览器探测：
1. **分析页面结构**：使用浏览器打开目标网站，观察登录流程和核心功能。
2. **监控网络请求**：在开发者工具（F12 -> Network）中寻找关键的 API 请求。
3. **识别鉴权信息**：确认登录所需的 Cookie（如 `session_id`, `token`等）和 Headers。

### 第二步：自动化凭证提取 (Credential Extraction)
使用 `templates/get_cookie_cdp.py.template` 作为蓝本，为新技能编写 `scripts/get_cookie_cdp.py`：
- **功能**：自动调起 Chrome (CDP 模式)，等待用户在浏览器中完成登录，然后自动抓取所需的 Cookie 并保存到 `config.json` 或 `.env`。
- **意义**：这消除了让用户手动复制 Cookie 的繁琐操作，也能在凭证失效时自动触发重登。

### 第三步：API 客户端实现 (Implementation)
参考 `templates/main.py.template` 编写核心逻辑：
- **封装 API**：使用 `requests` 封装探测到的接口。
- **集成凭证**：在构造函数中读取 `config.json` 中的凭证。
- **错误处理**：针对百度网盘等常见的“凭证过期”错误（如 errno: -6），提供清晰的排障建议。

### 第四步：编写技能文档 (Documentation)
参考 `templates/SKILL.md.template` 编写新技能的 `SKILL.md`：
- **自动化引导**：在文档顶部明确告诉 Agent，如果由于凭证缺失导致执行失败，应立即运行 `get_cookie_cdp.py` 进行自动修复。
- **渐进式披露**：对于复杂的 API 调用，先给出简单的示例，将复杂的参数说明放在后面。

---

## 🛠 调试与鲁棒性指南 (Debug & Robustness)

集成我们在实战中沉淀的调试经验：

1. **处理 JSON 解析错误**：
   - 现象：报错 `Expecting value: line 1 column 1`。
   - 诊断：这通常不是 JSON 格式问题，而是接口返回了 404、500 或 HTML 登录页。
   - 最佳实践：在 `main.py` 的 `try-except` 块中，**务必打印原始响应内容**（如 `resp.text`），以便快速定位是鉴权失败还是接口地址失效。

2. **接口选择策略 (REST vs. Web)**：
   - 如果使用开发者凭证（API Key/Secret），优先使用 REST API (`/rest/2.0/xpan`)。
   - 如果使用浏览器提取的 Cookie（BDUSS/STOKEN），优先尝试网页端原生接口（如 `/api/filemanager`, `/share/transfer`），这些接口对模拟登录的兼容性更好。

3. **多重鉴权保护 (CSRF/Token)**：
   - 现象：即使 Cookie 正确，写操作（如 POST）依然返回“非法请求”或 403。
   - 诊断：许多现代 Web 服务除了 Cookie 外，还需要动态令牌（如 `bdstoken`、`XSRF-TOKEN` 或 `authenticity_token`）。
   - 最佳实践：在 `WebServiceAPI` 的初始化方法中包含一个自动获取 Token 的私有方法，通常可以从页面 HTML 源码或某个特定的初始化接口（如 `/api/gettoken`）中提取。

---

## 🌟 最佳实践 (Best Practices)

- **无感排障**：当检测到鉴权错误码（如 `-6`）时，Agent 应优先静默尝试 `get_cookie_cdp.py`，而不是打扰用户。
- **环境嗅探**：在执行核心任务（如转存、删除）前，先调用一个轻量级的 `list` 接口，验证当前凭证是否真实可用。
- **多维度参数支持**：脚本应支持通过 `config.json`、环境变量以及命令行参数多渠道获取配置。

---

## 模板资源 (Templates)

在创建新技能时，请读取并应用以下模板内容：

- [Cookie 抓取模板 (基于 CDP)](./templates/get_cookie_cdp.py.template)
- [API 客户端主脚本模板](./templates/main.py.template)
- [技能文档 SKILL.md 模板](./templates/SKILL.md.template)

## 执行指南 (Guidelines)

1. **绝对路径**：在生成的 `SKILL.md` 中，调用脚本时务必提示 Agent 使用绝对路径或推导出的动态路径。
2. **隐私安全**：提醒用户不要将 `config.json` 或含有真实凭证的 `.env` 提交到 Git。
3. **渐进式复杂性**：先实现最核心的“读”功能，验证成功后再增加“写”操作。
