---
name: active-execution-guard
description: 当仓库可能存在 `docs/dev/ACTIVE.md` 且你即将开启新的复杂流程、切换任务主线或进入规划/实现主流程前使用
---

# 活动执行守卫

## 概述

只要仓库中存在 `docs/dev/ACTIVE.md`，就意味着当前有一个活动任务。活动任务在被处理之前，禁止进入任何新的复杂回答、规划、实现、文档修改或知识整理。

**核心原则：** `docs/dev/ACTIVE.md` 存在 = 有活动任务。

**边界原则：** 本技能用于阻止“新的复杂流程”，不是用来打断当前会话里的局部支持动作。对当前主线中的小修、小查、小验证，默认直接处理，不要求先弹出 `继续 / 挂起 / 放弃`。

## 使用时机

在以下任一情况出现时，先运行本技能：

- 你即将开启一个新的复杂任务流
- 你即将切换到与当前活动任务无关的另一条主线
- 你即将开始规划、roadmap、长链路实现、文档整理、知识沉淀或其他会持续多步的流程
- 你不知道仓库里是否存在活动任务

以下情况通常**不需要**触发本技能拦截：

- 当前会话里的局部 UI / 文案 / 样式微调
- 小范围 bug 修复或兼容性修正，且不改变任务主线
- 日志查看、单条命令重跑、只读排查
- 针对已有实现补一两个测试、调整输出格式、修复颜色/对齐/提示文案
- 明显属于“顺手支持动作”的小改动，且不会引入新的规划流或文档流

## 流程

### 第一步：检查活动任务

1. 检查 `docs/dev/ACTIVE.md` 是否存在。
2. 如果不存在：退出本技能，继续正常的技能发现与响应流程。
3. 如果存在：
   - 读取 `docs/dev/ACTIVE.md`
   - 根据其中的 `status_file` 读取对应任务目录下的 `STATUS.md`
   - 提取任务名、`task_id`、`lifecycle_status`、`phase`、最近摘要、下一步

### 第二步：阻止其他复杂流程

在活动任务被处理之前，不要直接开始新的复杂任务流程。只允许提示用户先处理当前任务。

如果当前请求满足上面的“小任务 / 支持动作”条件，则**不要**打断用户，不要弹 `继续 / 挂起 / 放弃`。直接处理，并保持：

- 不改写 `docs/dev/ACTIVE.md`
- 不切换任务目录
- 不把当前小任务升级成新的 roadmap / plan
- 不借机展开与用户请求无关的流程整理

使用类似下面的格式：

```text
检测到当前正在进行的任务：
- 任务：<任务名称>
- task_id：<task_id>
- lifecycle_status：<当前生命周期状态>
- phase：<当前阶段>
- 最近摘要：<最近摘要>
- 下一步：<下一步>

请选择：
1. 继续
2. 挂起
3. 放弃
```

### 第三步：处理用户选择

**如果用户选择 `继续`：**

- 基于 `ACTIVE.md` 与 `STATUS.md` 恢复执行
- 先回到当前任务，不要先回答不相关的新复杂请求
- 继续时应遵循当前任务的执行路径：`roadmap`、`executing-plans` 或 `subagent-driven-development`

**如果用户选择 `挂起`：**

- 更新任务目录中的 `STATUS.md`
  - `lifecycle_status` 设为 `hanging`
  - `active` 设为 `false`
  - 补充最近摘要与下一步
- 在任务目录的 `notes/` 下追加新的 `progress-*.md`
- 将任务目录移动到 `docs/dev/hanging/`
- 更新 `docs/dev/INDEX.md` 与 `docs/dev/hanging/INDEX.md`
- 删除 `docs/dev/ACTIVE.md`
- 完成后继续处理用户这次请求

**如果用户选择 `放弃`：**

- 更新任务目录中的 `STATUS.md`
  - `lifecycle_status` 设为 `abandoned`
  - `active` 设为 `false`
- 将任务目录移动到 `docs/dev/abandoned/`
- 更新 `docs/dev/INDEX.md`
- 删除 `docs/dev/ACTIVE.md`
- 完成后继续处理用户这次请求

## 完成边界

- 本技能**不提供** `完成` 选项
- `completed` 只能由执行技能在以下条件同时满足时自动产生：
  - 计划任务全部完成
  - 必要验证全部通过
  - 本轮应写入的 wiki 更新已完成

## ACTIVE.md 的最低要求

恢复执行前，`ACTIVE.md` 至少应包含：

- `task_id`
- `title`
- `task_dir`
- `lifecycle_status`
- `phase`
- `status_file`
- 最近摘要
- 下一步

如果它不完整，也不能绕过。它仍然代表一个活动任务，必须先处理。

## 红旗

**绝不：**

- 在检测到 `ACTIVE.md` 后先开始新的复杂任务
- 把当前主线里的小修、小查、小验证也误判为“新的复杂流程”
- 提供 `完成` 作为用户可选项
- 因为 `ACTIVE.md` 内容不完整就忽略它
- 把 `ACTIVE.md` 当成普通笔记而不是活动任务状态
- 在未完成 `挂起` 或 `放弃` 处理之前开始新复杂任务

## 集成

- `dev:using-booming`：任何响应前的全局入口
- `dev:executing-plans`：维护 `STATUS.md`、`ACTIVE.md`、`notes/progress-*.md` 与目录终态
- `dev:subagent-driven-development`：维护 `STATUS.md`、`ACTIVE.md`、`notes/progress-*.md` 与目录终态
