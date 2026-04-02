---
name: executing-plans
description: 当你有一个已写好的实现计划需要在独立会话中执行并设置审查检查点时使用
---

# 执行计划

## 概述

加载计划，批判性地审查，执行所有任务，维护 `docs/executions/CURRENT.md`，在完成后归档执行记录并汇报。

**开始时宣布：** "我正在使用 executing-plans 技能来实现这个计划。"

**注意：** 告诉 your human partner，Booming 在有子 Agent 访问权限时效果更好。如果在支持子 Agent 的平台（如 Claude Code 或 Codex）上运行，工作质量会显著提高。如果子 Agent 可用，请使用 dev:subagent-driven-development 替代本技能。

**前提：** 如果仓库可能存在 `docs/executions/CURRENT.md`，应先经过 `dev:active-execution-guard` 处理。

## 文档语言要求

除非用户明确要求其他语言，由本技能创建或更新的 `docs/executions/CURRENT.md`、执行归档、任务摘要、风险记录、阻塞说明都必须使用中文。文件名中的既有状态标识如 `completed`、`abandoned` 可保留原文；代码、命令、路径、标识符保持原文。

## 流程

### 第一步：加载并审查计划
1. 读取计划文件一次
2. 明确识别计划中的任务总数
3. 提取执行阶段需要的关键引用：
   - 设计文档路径
   - 计划文档路径
   - 每个任务的知识沉淀目标
4. 批判性地审查——识别计划中的任何问题或疑虑
5. 如有疑虑：在开始前与 your human partner 沟通
6. 如无疑虑：创建 TodoWrite，并创建或更新 `docs/executions/CURRENT.md`

### CURRENT.md 的最低内容

开始执行前，`docs/executions/CURRENT.md` 至少应写入：

- 设计文档路径
- 计划文档路径
- 当前状态
- 任务总数、已完成、进行中、未开始
- 已确认的重要上下文
- 用户已确认决策
- 当前约束
- 风险与阻塞
- 最近执行摘要
- 下一步

### 第二步：执行任务

对每个任务：
1. 标记为进行中
2. 严格按照每个步骤执行（计划中有细化的步骤）
3. 按规定运行验证
4. 更新 `docs/executions/CURRENT.md`
   - 当前进度
   - 最近执行摘要
   - 错误与纠正
   - 经验沉淀
   - 下一步
5. 判断是否产生长期有效知识
   - 如果有：使用 `dev:project-wiki-maintenance` 更新 `wiki/` 与 `INDEX.md`
   - 如果没有：在 `CURRENT.md` 中明确记录“本任务无 wiki 更新”
6. 标记为已完成

### 第三步：完成开发

所有任务完成并验证后，只有在以下条件都满足时，才允许归档为 `completed`：

- 计划任务全部完成
- 必要验证全部通过
- 本轮应写入的 wiki 更新已完成

满足后：
- 将当前执行归档到 `docs/executions/history/`
- 归档文件名使用 `execution-<YYYY-MM-DD-HH-mm>-<feature-name>-completed.md`
- 清理 `docs/executions/CURRENT.md`
- 宣布："我正在使用 finishing-a-development-branch 技能来完成这项工作。"
- **必需子技能：** 使用 dev:finishing-a-development-branch
- 遵循该技能来验证测试、展示选项、执行选择

### 放弃执行

如果用户通过 `active-execution-guard` 选择 `放弃`：

- 将当前执行归档到 `docs/executions/history/`
- 状态必须是 `abandoned`
- 清理 `docs/executions/CURRENT.md`
- 停止当前计划执行

## 何时停下来寻求帮助

**遇到以下情况立即停止执行：**
- 遇到阻塞（缺少依赖、测试失败、指令不清晰）
- 计划存在关键缺口导致无法开始
- 你不理解某条指令
- 验证反复失败

**寻求澄清而非猜测。** 在停下来之前，把新的风险、阻塞和下一步记录进 `CURRENT.md`。

## 何时重新审视早期步骤

**以下情况返回审查（第一步）：**
- 伙伴根据你的反馈更新了计划
- 基本方法需要重新思考

**不要强行突破阻塞**——停下来寻求帮助。

## 注意事项
- 先批判性地审查计划
- 在开始时确认任务总数
- 严格按照计划步骤执行
- 不要跳过验证
- 不要让 `CURRENT.md` 落后于真实状态
- 任务后优先更新 `CURRENT.md`，再移动到下一任务
- 长期知识进入 `wiki/`，执行流水留在 `docs/executions/`
- 计划提到技能时引用对应技能
- 遇到阻塞时停下来，不要猜测
- 未经用户明确同意，绝不在 main/master 分支上开始实现

## 集成

**必需的工作流技能：**
- **dev:active-execution-guard** - 必需：任何活动计划处理优先
- **dev:using-git-worktrees** - 必需：开始前设置隔离的工作空间
- **dev:writing-plans** - 创建本技能执行的计划
- **dev:project-wiki-maintenance** - 任务后写入长期项目知识
- **dev:finishing-a-development-branch** - 所有任务完成后收尾开发工作
