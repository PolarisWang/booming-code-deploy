---
name: executing-plans
description: 当你有一个已写好的实现计划需要在独立会话中执行并设置审查检查点时使用
---

# 执行计划

## 概述

加载计划，批判性地审查，执行所有任务，完成后汇报。

**开始时宣布：** "我正在使用 executing-plans 技能来实现这个计划。"

**注意：** 告诉 your human partner，Booming 在有子 Agent 访问权限时效果更好。如果在支持子 Agent 的平台（如 Claude Code 或 Codex）上运行，工作质量会显著提高。如果子 Agent 可用，请使用 booming-code:subagent-driven-development 替代本技能。

## 流程

### 第一步：加载并审查计划
1. 读取计划文件
2. 批判性地审查——识别计划中的任何问题或疑虑
3. 如有疑虑：在开始前与 your human partner 沟通
4. 如无疑虑：创建 TodoWrite 并继续

### 第二步：执行任务

对每个任务：
1. 标记为进行中
2. 严格按照每个步骤执行（计划中有细化的步骤）
3. 按规定运行验证
4. 标记为已完成

### 第三步：完成开发

所有任务完成并验证后：
- 宣布："我正在使用 finishing-a-development-branch 技能来完成这项工作。"
- **必需子技能：** 使用 booming-code:finishing-a-development-branch
- 遵循该技能来验证测试、展示选项、执行选择

## 何时停下来寻求帮助

**遇到以下情况立即停止执行：**
- 遇到阻塞（缺少依赖、测试失败、指令不清晰）
- 计划存在关键缺口导致无法开始
- 你不理解某条指令
- 验证反复失败

**寻求澄清而非猜测。**

## 何时重新审视早期步骤

**以下情况返回审查（第一步）：**
- 伙伴根据你的反馈更新了计划
- 基本方法需要重新思考

**不要强行突破阻塞**——停下来寻求帮助。

## 注意事项
- 先批判性地审查计划
- 严格按照计划步骤执行
- 不要跳过验证
- 计划提到技能时引用对应技能
- 遇到阻塞时停下来，不要猜测
- 未经用户明确同意，绝不在 main/master 分支上开始实现

## 集成

**必需的工作流技能：**
- **booming-code:using-git-worktrees** - 必需：开始前设置隔离的工作空间
- **booming-code:writing-plans** - 创建本技能执行的计划
- **booming-code:finishing-a-development-branch** - 所有任务完成后收尾开发工作
