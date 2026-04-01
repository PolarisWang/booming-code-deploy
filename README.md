# Booming-code

 是一套完整的软件开发工作流，专为代码智能体设计，基于一组可组合的"技能（skills）"和初始化指令构建，确保智能体能够正确使用这些技能。

## 工作原理

一切从你启动代码智能体的那一刻开始。当它感知到你在构建某个功能时，它**不会**直接跳进去写代码，而是退一步，先问清楚你真正想实现什么。

它通过对话引导出一份规格说明（spec），并以足够简短的片段逐步呈现给你，让你能够真正阅读和消化。

在你对设计点头认可之后，智能体会整理出一份清晰到足以让一个满怀热情的初级工程师——哪怕品味欠佳、判断力不足、毫无项目背景、且抗拒写测试——也能遵循的实现计划。计划中强调真正的红/绿 TDD、YAGNI（你不会需要它）和 DRY 原则。

接下来，当你说"开始吧"，它会启动一套**子智能体驱动的开发（subagent-driven-development）**流程：派遣子智能体逐一完成每个工程任务，检查并审查各自的工作，然后继续推进。Claude 能够持续自主工作数小时而不偏离你制定的计划，这并不罕见。

系统远不止这些，但以上是其核心。而且由于技能会自动触发，你不需要做任何特殊操作。你的代码智能体就这样拥有了超能力。


## 基本工作流

1. **brainstorming（头脑风暴）** — 在写代码之前激活。通过提问精炼粗糙想法，探索备选方案，分段呈现设计供验证，并保存设计文档。

2. **using-git-worktrees（使用 Git 工作树）** — 设计批准后激活。在新分支上创建隔离的工作空间，运行项目初始化，验证测试基线是否干净。

3. **writing-plans（编写计划）** — 在批准的设计基础上激活。将工作分解为小任务（每个 2-5 分钟）。每个任务都有精确的文件路径、完整的代码和验证步骤。

4. **subagent-driven-development（子智能体驱动开发）** 或 **executing-plans（执行计划）** — 基于计划激活。每个任务派发一个新鲜的子智能体，并通过两阶段审查（规格合规性审查 → 代码质量审查）；或按批次执行并设置人工检查点。

5. **test-driven-development（测试驱动开发）** — 实现过程中激活。强制执行"红-绿-重构"：先写失败的测试，看它失败，写最少量的代码，看它通过，提交。删除测试之前写的代码。

6. **requesting-code-review（请求代码审查）** — 在任务之间激活。对照计划进行审查，按严重程度报告问题。严重问题会阻止进度推进。

7. **finishing-a-development-branch（完成开发分支）** — 任务完成时激活。验证测试，呈现选项（合并/PR/保留/丢弃），清理工作树。

**智能体在任何任务前都会检查相关技能。** 这是强制工作流，不是建议。

## 内部组成

### 技能库

**测试**
- **test-driven-development** — 红-绿-重构循环（含测试反模式参考）

**调试**
- **systematic-debugging** — 4 阶段根因分析流程（含根因追踪、纵深防御、条件等待等技术）
- **verification-before-completion** — 确认问题已真正修复

**协作**
- **brainstorming** — 苏格拉底式设计精炼
- **writing-plans** — 详细实现计划
- **executing-plans** — 带检查点的批次执行
- **dispatching-parallel-agents** — 并发子智能体工作流
- **requesting-code-review** — 审查前检查清单
- **receiving-code-review** — 响应反馈
- **using-git-worktrees** — 并行开发分支
- **finishing-a-development-branch** — 合并/PR 决策工作流
- **subagent-driven-development** — 快速迭代，含两阶段审查（规格合规 → 代码质量）

**工具集成**
- **feishu-docs** — 飞书文档读写工具集，支持读取/导出/搜索/上传（详见下方）

**元技能**
- **writing-skills** — 按最佳实践创建新技能（含测试方法论）
- **using-booming** — 技能系统入门介绍

---

## feishu-docs — 飞书文档工具集,是一套完整的飞书文档读写 skill，基于飞书开放 API 实现。

### 快速上手

**配置（`.env`）：**
```
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_FOLDER_TOKEN=xxx   # 个人空间 folder_token，通过 feishu_auth.py 自动写入
```

**首次授权（获取个人空间 token）：**
```bash
python .claude/skills/tools-feishu-docs/feishu_auth.py
```

### 读取飞书文档

```bash
# 读取并输出 Markdown
python feishu_fetch.py "https://boomingtech.feishu.cn/wiki/xxx"

# 导出到本地文件
python feishu_fetch.py "https://..." --export-md output.md

# 搜索文档关键词
python feishu_fetch.py "https://..." --search "关键词"
```

### 上传 Markdown 到飞书

```bash
# 上传到个人空间（自动弹出浏览器授权）
python feishu_write.py --title "文档标题" input.md

# 设置分享权限
python feishu_write.py --title "标题" --share anyone input.md
# --share 选项：tenant（组织内可读，默认）/ anyone（所有人可读）/ closed（不分享）
```

### 支持的 URL 格式

| URL 格式 | 类型 |
|---------|------|
| `https://*.feishu.cn/docx/<token>` | 新版文档 |
| `https://*.feishu.cn/wiki/<token>` | 知识库 |
| `https://*.larkoffice.com/docx/<token>` | 海外版 |

### Claude Code 自动触发

当对话中出现飞书链接或"读取/上传飞书文档"时，skill 自动激活。

## 设计理念

- **测试驱动开发** — 始终先写测试
- **系统化胜于临时应对** — 流程优于猜测
- **降低复杂度** — 简洁是首要目标
- **证据优于断言** — 先验证，再宣布成功
