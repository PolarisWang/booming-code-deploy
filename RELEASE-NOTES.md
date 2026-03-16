## v1.3.0（2026-03-16）

### feishu-docs skill — 飞书文档完整读写能力

新增 `skills/feishu-docs/`，基于飞书开放 API 实现飞书文档的读取、搜索与写入。

**核心模块（`feishu/`）：**

| 模块 | 职责 |
|------|------|
| `parser.py` | 飞书分享 URL 解析（docx / wiki / larkoffice） |
| `auth.py` | tenant_access_token 获取与内存缓存（提前 5 分钟刷新） |
| `client.py` | 飞书 API 调用封装，含分页和 wiki 两步解析 |
| `converter.py` | 飞书 blocks → Markdown 转换（读取方向） |
| `searcher.py` | 文档关键词搜索，返回含上下文的匹配段落 |
| `writer.py` | Markdown → 飞书 blocks 转换（写入方向），参考 feishu-markdown 库 block type 编号体系 |

**CLI 工具：**

- `feishu_fetch.py` — 读取文档：`--export-md`、`--search`、`--json`
- `feishu_write.py` — 写入文档：`--share`（tenant/anyone/closed）、`--folder`
- `feishu_auth.py` — OAuth 浏览器授权，获取个人空间 folder_token

**关键技术细节：**

- 飞书写入 API 的 block_type 编号与读取 API **不同**（来自 feishu-markdown 库实证）：
  - Bullet = 12（读取侧为 9），Ordered = 13（读取侧为 10）
  - Code = 14（读取侧为 11），Quote = 15（读取侧为 12）
  - Paragraph 字段名为 `text`（非 `paragraph`），Divider 需 `divider: {}` 字段
- 行内样式解析：`**bold**`、`*italic*`、`~~strike~~`、`` `code` ``、`[link](url)`
- 上传到个人空间：通过 OAuth 获取 user_access_token，每次上传自动弹出浏览器授权，不持久化 token
- 文档权限设置：`drive/v1/permissions` API

**环境变量：**

```
FEISHU_APP_ID         飞书自建应用 App ID
FEISHU_APP_SECRET     飞书自建应用 App Secret
FEISHU_FOLDER_TOKEN   个人空间文件夹 token（通过 feishu_auth.py 自动写入）
FEISHU_DOMAIN         飞书文档域名（默认 boomingtech.feishu.cn）
```

---

## v1.2.0（2026-03-16）

### code-reviewer Agent 增强

**`agents/code-reviewer.md`** — 新增第 0 步：审查前自动执行 `git pull` 拉取最新代码，无论成功与否都继续后续审查步骤。

---

## v1.1.0（2026-03-15）

### Windows 测试基础设施

**为所有测试脚本新增 PowerShell 版本**

- `tests/claude-code/test-helpers.ps1` — 完整的 PowerShell 辅助函数库，对应 `test-helpers.sh`
  - `Run-Claude` — 带超时的子任务式 Claude 调用
  - `Assert-Contains` / `Assert-NotContains` — 带彩色输出的断言函数
  - `Assert-Count` / `Assert-Order` — 计数与顺序验证
  - `New-TestProject` / `Remove-TestProject` — 临时测试目录管理
  - `New-TestPlan` — 标准测试计划文件生成
- `tests/claude-code/test-subagent-driven-development.ps1` — 技能快速验证测试（对应 `.sh` 版），含 9 项断言
- `tests/claude-code/test-subagent-driven-development-integration.ps1` — 端到端集成测试（对应 `.sh` 版）
- `tests/claude-code/run-skill-tests.ps1` — 主测试运行器，支持 `--verbose`、`--test`、`--timeout`、`--integration` 参数，兼容 Windows PowerShell 5.1+

**测试运行对比：**

| 平台 | 命令 |
|------|------|
| Linux / macOS | `./run-skill-tests.sh` |
| Windows PowerShell | `.\run-skill-tests.ps1` |
| Windows（集成测试） | `.\run-skill-tests.ps1 --integration` |

### 文档中文化

- `README.md` — 全文中文翻译，保留所有代码块和命令原文
- `RELEASE-NOTES.md` — 重写为 booming-code 专属中文发版说明
- `tests/claude-code/README.md` — 新增 Windows/PowerShell 使用说明和命令对比表

---

## v1.0.0（2026-03-15）

### 基于 obra/superpowers v5.0.2 初始化

Fork 并初始化完整技能体系，包含 14 个技能、3 类测试套件、所有钩子和文档。

### Windows 原生支持

**环境初始化脚本 `init.bat`**

Windows 用户一键启动脚本，双击即可完成初始化：

- 自动检测 `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_BASE_URL` 是否已配置
- 若未配置，交互式引导输入并写入系统/用户环境变量（`setx`）
- 自动查找并打开 VS Code（检测 `%LOCALAPPDATA%`、`%ProgramFiles%` 及 PATH）
- 未找到 VS Code 时回退尝试 Cursor
- 两者均未安装时给出友好提示，无崩溃退出

**头脑风暴服务器 Windows 脚本**

- `skills/booming-code-brainstorm/scripts/start-server.bat` — 对应 `start-server.sh` 的完整 Windows 实现
  - 随机高端口启动，输出 JSON 格式连接信息
  - 支持 `--project-dir`、`--host`、`--url-host`、`--foreground`、`--background` 参数
  - 会话文件存储在 `<project-dir>\.booming\brainstorm\`
  - 后台模式通过 `start /b` 实现，PID 写入会话目录供 `stop-server.bat` 使用
- `skills/booming-code-brainstorm/scripts/stop-server.bat` — 对应 `stop-server.sh` 的完整 Windows 实现
  - 读取 PID 文件并调用 `taskkill /F /PID` 终止服务器进程
  - 清理会话状态文件

**调试工具 Windows 脚本**

- `skills/booming-code-systematic-debugging/find-polluter.bat` — 对应 `find-polluter.sh` 的 Windows 批处理实现
  - 二分查找污染测试文件/状态的脚本
  - 用法：`find-polluter.bat <要检查的文件或目录> <测试模式>`
  - 示例：`find-polluter.bat ".git" "src\**\*.test.ts"`

**Windows 文档**

- `docs/windows/polyglot-hooks.md` — Windows 多语言钩子（polyglot hooks）原理与问题排查指南
  - 解释 `.sh` 自动检测的历史变更
  - 记录 `run-hook.cmd` 包装器的工作原理
  - 覆盖路径含空格、CRLF 换行、MSYS 兼容性等常见问题

### 钩子配置

`hooks/hooks.json` — 配置 SessionStart 钩子，通过 `run-hook.cmd` 多语言包装器执行，确保在 Windows cmd.exe、Git Bash、PowerShell 和 Unix 环境中均可正常启动 `session-start` 脚本。

`hooks/session-start`（无扩展名）— 平台自适应的会话启动脚本：
- 读取 `using-booming` 技能内容并注入会话上下文
- 针对 Claude Code 发送 `hookSpecificOutput`，针对其他平台（Cursor 等）发送 `additional_context`，防止上下文双重注入

### 技能体系（继承自 superpowers v5.0.2）

完整 14 个技能，路径均在 `skills/` 下：

| 分类 | 技能 | 关键文件 |
|------|------|----------|
| 启动 | `using-booming` | `SKILL.md`，`references/codex-tools.md`，`references/gemini-tools.md` |
| 设计 | `booming-code-brainstorm` | `SKILL.md`，`visual-companion.md`，`spec-document-reviewer-prompt.md`，`scripts/` |
| 规划 | `writing-plans` | `SKILL.md`，`plan-document-reviewer-prompt.md` |
| 开发 | `subagent-driven-development` | `SKILL.md`，`implementer-prompt.md`，`spec-reviewer-prompt.md`，`code-quality-reviewer-prompt.md` |
| 开发 | `executing-plans` | `SKILL.md` |
| 开发 | `dispatching-parallel-agents` | `SKILL.md` |
| 开发 | `using-git-worktrees` | `SKILL.md` |
| 测试 | `test-driven-development` | `SKILL.md`，`testing-anti-patterns.md` |
| 调试 | `systematic-debugging` | `SKILL.md`，`root-cause-tracing.md`，`defense-in-depth.md`，`condition-based-waiting.md`，`find-polluter.sh`，`find-polluter.bat` |
| 调试 | `verification-before-completion` | `SKILL.md` |
| 协作 | `requesting-code-review` | `SKILL.md`，`code-reviewer.md` |
| 协作 | `receiving-code-review` | `SKILL.md` |
| 协作 | `finishing-a-development-branch` | `SKILL.md` |
| 元技能 | `writing-skills` | `SKILL.md`，`anthropic-best-practices.md`，`graphviz-conventions.dot`，`persuasion-principles.md`，`render-graphs.js` |

### 测试套件（继承自 superpowers v5.0.2，新增 Windows 脚本）

**`tests/claude-code/`** — Claude Code 无头测试

- `run-skill-tests.sh` / `run-skill-tests.ps1` — 主测试运行器（跨平台）
- `test-helpers.sh` / `test-helpers.ps1` — 辅助函数库（跨平台）
- `test-subagent-driven-development.sh` / `.ps1` — 技能快速验证（~2 分钟）
- `test-subagent-driven-development-integration.sh` / `.ps1` — 端到端工作流测试（10-30 分钟）
- `test-document-review-system.sh` — 文档审查系统测试
- `analyze-token-usage.py` — 会话令牌用量分析（需 Python 3）

**`tests/brainstorm-server/`** — 头脑风暴服务器单元测试

- `server.test.js` — HTTP 服务、WebSocket 协议、文件监听集成测试
- `ws-protocol.test.js` — RFC 6455 帧格式、ping/pong、关闭握手测试

**`tests/skill-triggering/`** — 技能触发验证

验证 6 个技能能通过朴素自然语言描述触发，无需明确命名：
`booming-code-brainstorm`、`test-driven-development`、`systematic-debugging`、`writing-plans`、`executing-plans`、`requesting-code-review`

**`tests/explicit-skill-requests/`** — 明确请求场景测试

9 种不同用户措辞下的技能触发验证：直接请求、行动导向、跳过形式、对话中段等。

**`tests/subagent-driven-dev/`** — 端到端工作流测试项目

- `go-fractals/` — Go CLI 工具（Sierpinski/Mandelbrot，10 个任务）
- `svelte-todo/` — Svelte CRUD 应用（localStorage + Playwright，12 个任务）

### 智能体

`agents/code-reviewer.md` — `superpowers:code-reviewer` 智能体定义，提供针对计划和编码标准的系统化代码审查。
