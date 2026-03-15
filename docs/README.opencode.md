# Booming 用于 OpenCode

在 [OpenCode.ai](https://opencode.ai) 中使用 Booming 的完整指南。

## 快速安装

告诉 OpenCode：

```
将 https://github.com/obra/booming 克隆到 ~/.config/opencode/booming，然后创建目录 ~/.config/opencode/plugins，然后将 ~/.config/opencode/booming/.opencode/plugins/booming.js 符号链接到 ~/.config/opencode/plugins/booming.js，然后将 ~/.config/opencode/booming/skills 符号链接到 ~/.config/opencode/skills/booming，然后重启 opencode。
```

## 手动安装

### 前提条件

- 已安装 [OpenCode.ai](https://opencode.ai)
- 已安装 Git

### macOS / Linux

```bash
# 1. 安装 Booming（或更新现有安装）
if [ -d ~/.config/opencode/booming ]; then
  cd ~/.config/opencode/booming && git pull
else
  git clone https://github.com/obra/booming.git ~/.config/opencode/booming
fi

# 2. 创建目录
mkdir -p ~/.config/opencode/plugins ~/.config/opencode/skills

# 3. 如果存在则删除旧符号链接/目录
rm -f ~/.config/opencode/plugins/booming.js
rm -rf ~/.config/opencode/skills/booming

# 4. 创建符号链接
ln -s ~/.config/opencode/booming/.opencode/plugins/booming.js ~/.config/opencode/plugins/booming.js
ln -s ~/.config/opencode/booming/skills ~/.config/opencode/skills/booming

# 5. 重启 OpenCode
```

#### 验证安装

```bash
ls -l ~/.config/opencode/plugins/booming.js
ls -l ~/.config/opencode/skills/booming
```

两者都应该显示指向 booming 目录的符号链接。

### Windows

**前提条件：**
- 已安装 Git
- 启用了**开发者模式**或具有**管理员权限**
  - Windows 10：设置 → 更新与安全 → 面向开发者
  - Windows 11：设置 → 系统 → 面向开发者

选择你的 shell：[命令提示符](#命令提示符) | [PowerShell](#powershell) | [Git Bash](#git-bash)

#### 命令提示符

以管理员身份运行，或启用开发者模式：

```cmd
:: 1. 安装 Booming
git clone https://github.com/obra/booming.git "%USERPROFILE%\.config\opencode\booming"

:: 2. 创建目录
mkdir "%USERPROFILE%\.config\opencode\plugins" 2>nul
mkdir "%USERPROFILE%\.config\opencode\skills" 2>nul

:: 3. 删除现有链接（重新安装时安全）
del "%USERPROFILE%\.config\opencode\plugins\booming.js" 2>nul
rmdir "%USERPROFILE%\.config\opencode\skills\booming" 2>nul

:: 4. 创建插件符号链接（需要开发者模式或管理员）
mklink "%USERPROFILE%\.config\opencode\plugins\booming.js" "%USERPROFILE%\.config\opencode\booming\.opencode\plugins\booming.js"

:: 5. 创建技能 junction（无需特殊权限）
mklink /J "%USERPROFILE%\.config\opencode\skills\booming" "%USERPROFILE%\.config\opencode\booming\skills"

:: 6. 重启 OpenCode
```

#### PowerShell

以管理员身份运行，或启用开发者模式：

```powershell
# 1. 安装 Booming
git clone https://github.com/obra/booming.git "$env:USERPROFILE\.config\opencode\booming"

# 2. 创建目录
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.config\opencode\plugins"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.config\opencode\skills"

# 3. 删除现有链接（重新安装时安全）
Remove-Item "$env:USERPROFILE\.config\opencode\plugins\booming.js" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.config\opencode\skills\booming" -Force -ErrorAction SilentlyContinue

# 4. 创建插件符号链接（需要开发者模式或管理员）
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.config\opencode\plugins\booming.js" -Target "$env:USERPROFILE\.config\opencode\booming\.opencode\plugins\booming.js"

# 5. 创建技能 junction（无需特殊权限）
New-Item -ItemType Junction -Path "$env:USERPROFILE\.config\opencode\skills\booming" -Target "$env:USERPROFILE\.config\opencode\booming\skills"

# 6. 重启 OpenCode
```

#### Git Bash

注意：Git Bash 的原生 `ln` 命令复制文件而不是创建符号链接。改用 `cmd //c mklink`（`//c` 是 Git Bash 的 `/c` 语法）。

```bash
# 1. 安装 Booming
git clone https://github.com/obra/booming.git ~/.config/opencode/booming

# 2. 创建目录
mkdir -p ~/.config/opencode/plugins ~/.config/opencode/skills

# 3. 删除现有链接（重新安装时安全）
rm -f ~/.config/opencode/plugins/booming.js 2>/dev/null
rm -rf ~/.config/opencode/skills/booming 2>/dev/null

# 4. 创建插件符号链接（需要开发者模式或管理员）
cmd //c "mklink \"$(cygpath -w ~/.config/opencode/plugins/booming.js)\" \"$(cygpath -w ~/.config/opencode/booming/.opencode/plugins/booming.js)\""

# 5. 创建技能 junction（无需特殊权限）
cmd //c "mklink /J \"$(cygpath -w ~/.config/opencode/skills/booming)\" \"$(cygpath -w ~/.config/opencode/booming/skills)\""

# 6. 重启 OpenCode
```

#### WSL 用户

如果在 WSL 内运行 OpenCode，改用 [macOS / Linux](#macos--linux) 说明。

#### 验证安装

**命令提示符：**
```cmd
dir /AL "%USERPROFILE%\.config\opencode\plugins"
dir /AL "%USERPROFILE%\.config\opencode\skills"
```

**PowerShell：**
```powershell
Get-ChildItem "$env:USERPROFILE\.config\opencode\plugins" | Where-Object { $_.LinkType }
Get-ChildItem "$env:USERPROFILE\.config\opencode\skills" | Where-Object { $_.LinkType }
```

在输出中查找 `<SYMLINK>` 或 `<JUNCTION>`。

#### Windows 故障排除

**"没有足够的权限"错误：**
- 在 Windows 设置中启用开发者模式，或
- 右键点击终端 → "以管理员身份运行"

**"当文件已存在时无法创建文件"：**
- 先运行删除命令（步骤 3），然后重试

**git clone 后符号链接不起作用：**
- 运行 `git config --global core.symlinks true` 并重新克隆

## 使用方法

### 查找技能

使用 OpenCode 的原生 `skill` 工具列出所有可用技能：

```
use skill tool to list skills
```

### 加载技能

使用 OpenCode 的原生 `skill` 工具加载特定技能：

```
use skill tool to load booming/brainstorming
```

### 个人技能

在 `~/.config/opencode/skills/` 中创建你自己的技能：

```bash
mkdir -p ~/.config/opencode/skills/my-skill
```

创建 `~/.config/opencode/skills/my-skill/SKILL.md`

### 项目技能

在你的 OpenCode 项目中创建项目特定技能：

```bash
# 在你的 OpenCode 项目中
mkdir -p .opencode/skills/my-project-skill
```

## 技能位置

OpenCode 从这些位置发现技能：

1. **项目技能**（`.opencode/skills/`）- 最高优先级
2. **个人技能**（`~/.config/opencode/skills/`）
3. **Booming 技能**（`~/.config/opencode/skills/booming/`）- 通过符号链接

## 功能

### 自动上下文注入

插件通过 `experimental.chat.system.transform` 钩子自动注入 booming 上下文。这在每次请求时将"using-booming"技能内容添加到系统提示中。

### 原生技能集成

Booming 使用 OpenCode 的原生 `skill` 工具进行技能发现和加载。技能被符号链接到 `~/.config/opencode/skills/booming/`，因此它们与你的个人和项目技能一起出现。

## 更新

```bash
cd ~/.config/opencode/booming
git pull
```

重启 OpenCode 以加载更新。

## 故障排除

### 插件未加载

1. 检查插件是否存在：`ls ~/.config/opencode/booming/.opencode/plugins/booming.js`
2. 检查符号链接/junction：`ls -l ~/.config/opencode/plugins/`
3. 检查 OpenCode 日志：`opencode run "test" --print-logs --log-level DEBUG`

### 未找到技能

1. 验证技能符号链接：`ls -l ~/.config/opencode/skills/booming`（应指向 booming/skills/）
2. 使用 OpenCode 的 `skill` 工具列出可用技能
3. 检查技能结构：每个技能需要一个带有有效前置元数据的 `SKILL.md` 文件

## 获取帮助

- 报告问题：https://github.com/obra/booming/issues
- 主要文档：https://github.com/obra/booming
- OpenCode 文档：https://opencode.ai/docs/
