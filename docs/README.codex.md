# Booming 用于 Codex

通过原生技能发现，在 OpenAI Codex 中使用 Booming 的指南。

## 快速安装

告诉 Codex：

```
从 https://raw.githubusercontent.com/obra/booming/refs/heads/main/.codex/INSTALL.md 获取并遵循指令
```

## 手动安装

### 前提条件

- OpenAI Codex CLI
- Git

### 步骤

1. 克隆仓库：
   ```bash
   git clone https://github.com/obra/booming.git ~/.codex/booming
   ```

2. 创建技能符号链接：
   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/booming/skills ~/.agents/skills/booming
   ```

3. 重启 Codex。

4. **对于子 Agent 技能**（可选）：像 `dispatching-parallel-agents` 和 `subagent-driven-development` 这样的技能需要 Codex 的 collab 功能。添加到你的 Codex 配置：
   ```toml
   [features]
   collab = true
   ```

### Windows

使用 junction 代替符号链接（不需要开发者模式）：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\booming" "$env:USERPROFILE\.codex\booming\skills"
```

## 工作原理

Codex 具有原生技能发现功能——它在启动时扫描 `~/.agents/skills/`，解析 SKILL.md 前置元数据，并按需加载技能。Booming 技能通过单个符号链接变得可见：

```
~/.agents/skills/booming/ → ~/.codex/booming/skills/
```

`using-booming` 技能会被自动发现并强制执行技能使用纪律——不需要额外配置。

## 使用方法

技能会被自动发现。Codex 在以下情况激活它们：
- 你按名称提及技能（例如，"使用 brainstorming"）
- 任务与技能描述匹配
- `using-booming` 技能指示 Codex 使用某个技能

### 个人技能

在 `~/.agents/skills/` 中创建你自己的技能：

```bash
mkdir -p ~/.agents/skills/my-skill
```

创建 `~/.agents/skills/my-skill/SKILL.md`：

```markdown
---
name: my-skill
description: 当 [条件] 时使用 - [它做什么]
---

# 我的技能

[你的技能内容在这里]
```

`description` 字段是 Codex 决定何时自动激活技能的方式——将其写成清晰的触发条件。

## 更新

```bash
cd ~/.codex/booming && git pull
```

技能通过符号链接立即更新。

## 卸载

```bash
rm ~/.agents/skills/booming
```

**Windows（PowerShell）：**
```powershell
Remove-Item "$env:USERPROFILE\.agents\skills\booming"
```

可选地删除克隆：`rm -rf ~/.codex/booming`（Windows：`Remove-Item -Recurse -Force "$env:USERPROFILE\.codex\booming"`）。

## 故障排除

### 技能未显示

1. 验证符号链接：`ls -la ~/.agents/skills/booming`
2. 检查技能是否存在：`ls ~/.codex/booming/skills`
3. 重启 Codex——技能在启动时发现

### Windows junction 问题

Junction 通常不需要特殊权限就能工作。如果创建失败，尝试以管理员身份运行 PowerShell。

## 获取帮助

- 报告问题：https://github.com/obra/booming/issues
- 主要文档：https://github.com/obra/booming
