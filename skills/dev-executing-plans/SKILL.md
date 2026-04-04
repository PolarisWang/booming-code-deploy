---
name: executing-plans
description: 当你有一个已写好的实现计划需要在独立会话中执行并设置审查检查点时使用
---

# 执行计划

## 概述

加载计划，批判性地审查，执行所有任务，并维护当前任务目录中的 `STATUS.md`、`docs/dev/ACTIVE.md`、`notes/progress-*.md` 与索引文件。

**开始时宣布：** "我正在使用 executing-plans 技能来实现这个计划。"

**注意：** 如果有可用子 Agent，应优先使用 `dev:subagent-driven-development`。

**前提：** 如果仓库可能存在 `docs/dev/ACTIVE.md`，应先经过 `dev:active-execution-guard` 处理。

## 文档语言要求

除非用户明确要求其他语言，由本技能创建或更新的 `STATUS.md`、`ACTIVE.md`、`notes/progress-*.md`、索引摘要、风险记录、阻塞说明都必须使用中文。代码、命令、路径、标识符保持原文。

## 第一步：加载并审查计划

1. 读取当前任务目录中的计划文件一次
2. 明确识别计划中的任务总数
3. 提取执行需要的关键引用：
   - 设计文档路径
   - 计划文档路径
   - 每个任务的知识沉淀目标
4. 批判性审查计划，识别任何疑虑
5. 如无疑虑：创建 TodoWrite，并创建或更新：
   - 当前任务目录中的 `STATUS.md`
   - `docs/dev/ACTIVE.md`
   - `docs/dev/INDEX.md` 与对应生命周期索引

## 第二步：执行任务

对每个任务：

1. 标记进入 `executing`
2. 严格按照计划步骤执行
3. 按规定运行验证
4. 更新 `STATUS.md`
   - 最近摘要
   - 下一步
   - 风险与阻塞
5. 更新 `docs/dev/ACTIVE.md`
6. 追加 `notes/progress-*.md`
7. 更新索引文件
8. 判断是否产生长期有效知识
   - 如果有：使用 `dev:project-wiki-maintenance`
   - 如果没有：在 `STATUS.md` 的最近摘要或新的 `notes/progress-*.md` 中明确记录“本任务无 wiki 更新”

## 第三步：完成开发

所有任务完成并验证后，只有在以下条件都满足时，才允许归档为 `completed`：

- 计划任务全部完成
- 必要验证全部通过
- 本轮应写入的 wiki 更新已完成

满足后：

- 更新 `STATUS.md`
  - `lifecycle_status` 设为 `completed`
  - `active` 设为 `false`
- 将任务目录移动到 `docs/dev/completed/`
- 删除 `docs/dev/ACTIVE.md`
- 更新索引文件
- 宣布："我正在使用 finishing-a-development-branch 技能来完成这项工作。"
- 使用 `dev:finishing-a-development-branch`

## 放弃执行

如果用户通过 `active-execution-guard` 选择 `放弃`：

- 将任务目录移动到 `docs/dev/abandoned/`
- 状态必须是 `abandoned`
- 删除 `docs/dev/ACTIVE.md`
- 更新索引
- 停止当前计划执行

## 何时停下来寻求帮助

遇到以下情况立即停止执行：

- 遇到阻塞（缺少依赖、测试失败、指令不清晰）
- 计划存在关键缺口导致无法开始
- 你不理解某条指令
- 验证反复失败

在停下来之前，把新的风险、阻塞和下一步记录进 `STATUS.md` 与最新 `notes/progress-*.md`。

## 注意事项

- 先批判性审查计划
- 在开始时确认任务总数
- 严格按照计划步骤执行
- 不要跳过验证
- 不要让 `STATUS.md`、`ACTIVE.md` 或索引落后于真实状态
- 长期知识进入 `wiki/`，执行流水留在任务目录的 `notes/`

## 集成

- `dev:active-execution-guard`
- `dev:using-git-worktrees`
- `dev:writing-plans`
- `dev:project-wiki-maintenance`
- `dev:finishing-a-development-branch`
