---
name: writing-plans
description: 当你有规格说明或多步骤任务的需求时，在接触代码之前使用
---

# 编写计划

## 概述

编写全面的实现计划，假设工程师对我们的代码库完全没有上下文且品味存疑。记录他们需要了解的一切：每个任务需要触及哪些文件、代码、可能需要查阅的测试和文档，以及如何测试。将整个计划拆分为可执行的细化任务。DRY。YAGNI。TDD。频繁提交。

计划不仅要告诉执行者“做什么”，还要让执行阶段能够稳定维护 `docs/executions/CURRENT.md` 和后续的 wiki 知识沉淀。

假设他们是熟练的开发者，但对我们的工具集或问题域几乎一无所知。假设他们对好的测试设计了解不多。

**开始时宣布：** "我正在使用 writing-plans 技能来创建实现计划。"

**上下文：** 应在专用的 worktree 中运行（由 brainstorming 技能创建）。

**保存计划到：** `docs/booming/<YYYY-MM-DD>-<feature-name>/plan-<YYYY-MM-DD-HH>-<feature-name>.md`
- （用户的计划位置偏好会覆盖此默认值）

## 范围检查

如果规格说明涵盖多个独立子系统，应该在头脑风暴阶段就拆分为子项目规格。如果没有拆分，建议将其拆分为独立计划——每个子系统一个。每个计划应能独立产出可工作、可测试的软件。

## 文件结构

在定义任务之前，梳理出哪些文件将被创建或修改，以及每个文件的职责。这是分解决策被锁定的地方。

- 设计具有清晰边界和定义良好接口的单元。每个文件应有一个明确的职责。
- 你对能一次性在脑中持有的代码推理最好，当文件专注时你的编辑也更可靠。优先选择较小的专注文件，而非做太多事情的大文件。
- 经常一起变更的文件应放在一起。按职责拆分，而非按技术层级拆分。
- 在现有代码库中，遵循已建立的模式。如果代码库使用大文件，不要单方面重构——但如果你正在修改的文件已变得难以管理，在计划中包含拆分是合理的。

这个结构为任务分解提供依据。每个任务应产出独立有意义的自包含变更。

## 细化任务粒度

**每个步骤是一个操作（2-5 分钟）：**
- "编写失败测试" - 步骤
- "运行它以确认失败" - 步骤
- "实现使测试通过的最小代码" - 步骤
- "运行测试并确认通过" - 步骤
- "提交" - 步骤

## 计划文档头部

**每个计划必须以此头部开始：**

```markdown
# [功能名称] 实现计划

> **For agentic workers:** REQUIRED: Use dev:subagent-driven-development (if subagents available) or dev:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** [一句话描述这要构建什么]

**架构：** [2-3 句关于方法的描述]

**技术栈：** [关键技术/库]

**设计文档：** [design 文档路径]

**预期知识沉淀：** [主要 wiki 目标路径，或“按任务决定”]

---
```

## 任务结构

````markdown
### 任务 N：[组件名称]

**文件：**
- 创建：`exact/path/to/file.py`
- 修改：`exact/path/to/existing.py:123-145`
- 测试：`tests/exact/path/to/test.py`

**知识沉淀：**
- 目标：`wiki/...` 或 `无`
- 原因：[为什么这个任务会或不会产生长期知识]

- [ ] **步骤 1：编写失败测试**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/path/test.py::test_name -v`
预期：FAIL，显示 "function not defined"

- [ ] **步骤 3：编写最小实现**

```python
def function(input):
    return expected
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/path/test.py::test_name -v`
预期：PASS

- [ ] **步骤 5：提交**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## 注意事项
- 始终使用精确的文件路径
- 计划中包含完整代码（而非"添加验证"这样的描述）
- 精确的命令及预期输出
- 用 @ 语法引用相关技能
- 不要让执行者猜设计文档路径、任务总数或知识沉淀落点
- DRY、YAGNI、TDD、频繁提交

## 计划审查循环

完成每个计划块后：

1. 派发计划文档审查者子 Agent（见 plan-document-reviewer-prompt.md），提供精心构建的审查上下文——绝不使用你的会话历史。这使审查者专注于计划本身，而非你的思考过程。
   - 提供：块内容、规格文档路径
2. 如果 ❌ 发现问题：
   - 修复该块中的问题
   - 重新派发审查者审查该块
   - 重复直到 ✅ 批准
3. 如果 ✅ 批准：继续下一块（如果是最后一块则交接执行）

**块边界：** 使用 `## Chunk N: <name>` 标题来划定块。每块应 ≤1000 行且逻辑自包含。

**审查循环指导：**
- 编写计划的同一 Agent 修复它（保留上下文）
- 如果循环超过 5 次迭代，向人类寻求指导
- 审查者是顾问——如果你认为反馈不正确，解释你的不同意见

## 执行交接

保存计划后：

**"计划已完成并保存到 `docs/booming/<YYYY-MM-DD>-<feature-name>/plan-<YYYY-MM-DD-HH>-<feature-name>.md`。准备好执行了吗？"**

**执行路径取决于执行环境的能力：**

**如果执行环境有子 Agent（Claude Code 等）：**
- **必需：** 使用 dev:subagent-driven-development
- 不要提供选择——子 Agent 驱动是标准方法
- 每个任务使用新鲜的子 Agent + 两阶段审查

**如果执行环境没有子 Agent：**
- 使用 dev:executing-plans 在当前会话中执行计划
- 批量执行，设置检查点供审查
