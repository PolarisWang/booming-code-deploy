---
name: booming-analysis-tracy-selection
description: 当用户提出 Tracy 性能分析问题时使用——如"这个函数为什么慢"、"帮我分析当前选中的区域"、"分析这个 trace"。要求 Tracy Profiler UI 已打开（localhost:9090-9099）。不适用于纯概念性 Tracy 问题。
---

# Tracy 交互式性能分析

通过 Tracy Profiler UI 的 HTTP API，读取用户在 UI 中选中的 zone，进行交互式深入分析。

## 脚本：tracy_http.py

Tracy Profiler UI HTTP 客户端，专为 agent 调用设计（纯标准库，无第三方依赖）。
自动扫描端口 9090-9099，验证 trace 文件已加载，所有输出为 JSON。

| 命令 | 调用方式 | 作用 |
|------|----------|------|
| `filepath` | `python .claude/script/tracy/tracy_http.py filepath` | 扫描 9090-9099，找到正在运行且已打开 trace 文件的 Tracy UI。端口验证逻辑：请求 `/api/filepath` 并检查返回的 `filepath` 字段非空，避免连接到未加载文件的 Tracy 实例。 |
| `selection` | `python .claude/script/tracy/tracy_http.py selection` | 读取 Tracy UI 当前高亮选中的 zone 完整数据，包含函数名、线程信息、父子 zone 关系、源文件位置及精确耗时。`valid: false` 表示 Tracy UI 中当前没有选中任何 zone。 |
| `zone <id>` | `python .claude/script/tracy/tracy_http.py zone 12345` | 按 zone_id 查询单个 zone 详情，返回字段结构与 `selection` 完全相同。用途：递归遍历 `children_ids` 展开调用树，或从父 zone 向下钻取热点。 |

**错误处理行为**（来自代码实现）：

| 情形 | 返回值 | exit code |
|------|--------|-----------|
| 端口 9090-9099 均无响应或无已加载文件 | `{"error": "Tracy Profiler UI not found on ports 9090-9099..."}` | 1 |
| HTTP 错误（如 404） | `{"error": "HTTP 404: Not Found"}` | 1 |
| 调用成功 | 正常 JSON 数据（含 `"port"` 字段） | 0 |

超时设置：端口扫描 1.0s/端口，API 查询 5.0s。

## 工作流

### 阶段 1：连接 Tracy Profiler UI

```bash
python .claude/script/tracy/tracy_http.py filepath
```

返回 `{"filepath": "...", "port": 9090}` 表示连接成功。
返回 `{"error": "..."}` 时告知用户打开 Tracy Profiler 并加载 trace 文件。

### 阶段 2：读取当前选中 zone

```bash
python .claude/script/tracy/tracy_http.py selection
```

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `valid` | bool | false = 当前无选中 zone |
| `zone_id` | int | zone 唯一标识 |
| `parent_id` | int | 父 zone ID（-1 表示根）|
| `children_ids` | int[] | 直接子 zone 的 ID 列表 |
| `name` | string | zone 标签名 |
| `function` | string | 完整函数名（含类名）|
| `file` | string | 源文件路径 |
| `line` | int | 源码行号 |
| `start_ns` | int | 开始时间（纳秒）|
| `duration_ns` | int | 耗时（纳秒）|

**`valid: false` 时：** 提示用户 "请在 Tracy UI 中点击选择一个 zone，我会立即分析它。"

### 阶段 3：分析选中 zone

展示基本信息时，将纳秒转为毫秒（`duration_ns / 1_000_000`）：

```
函数：MyClass::MyFunction (src/myclass.cpp:42)
耗时：5.23 ms
子 zone 数：3
```

根据用户问题选择分析策略：

#### 热点定位

对每个 `children_ids` 调用脚本获取子 zone 耗时：

```bash
python .claude/script/tracy/tracy_http.py zone <zone_id>
```

计算热点：
- 找出耗时最长的子 zone，并计算其占父 zone 耗时的百分比（`child_ns / parent_ns * 100`）
- 计算：父耗时 - 所有子耗时之和 = 非 zone 代码耗时（内联调用、系统调用等）
- 按耗时降序展示子 zone 列表，每项附带占比（如"FunctionA: 2.1ms (42%)"）

#### 调用树展开

递归展开子 zone，优先展开耗时较大的节点。

#### 上下文关联

结合 `file` + `line` 定位源码，告知用户具体位置供代码对照分析。

#### 阶段 3 结尾：本地文件检测与代码优化提示

热点 zone 分析完成后，按以下顺序查找源文件，找到即停止：

**步骤 1：原路径直接检查**

```bash
python -c "import os; print(os.path.exists(r'{file}'))"
```

文件存在则进入"文件找到"流程。

**步骤 2：工程目录模糊搜索**

取文件名（去掉路径），在当前工作目录递归搜索：

```bash
python {skill_dir}/../script/tracy/find_file.py "{file}"
```

有匹配结果时，若只有一个直接使用；多个时展示列表让用户选择。

**步骤 3：用户指定根目录**

步骤 1、2 均未找到时，提示用户：
> "未找到源文件 `{filename}`，请输入项目根目录路径，我来继续搜索："

用户输入后，以用户提供的根目录重新执行搜索：

```bash
python {skill_dir}/../script/tracy/find_file.py "{file}" "<用户输入根目录>"
```

仍未找到则告知：
> "在指定目录下未找到 `{filename}`，跳过代码级分析。"

---

**文件找到时**：提示用户：
> "是否对热点函数 `{function}` 进行代码优化分析？"

用户确认后调用 `booming-analysis-code-optimization` skill，传入：
- 热点 zone 的完整 JSON（函数名、**本地实际文件路径**、行号、耗时、子 zone 耗时分布）
- 用户的原始问题描述

**最终未找到时**：告知用户：
> "源文件 `{file}` 在本地不可访问，跳过代码级分析。"

## HTTP API 速查

| 端点 | 用途 |
|------|------|
| `GET /api/filepath` | 确认 trace 文件已加载 |
| `GET /api/current_selection` | 读取 UI 当前选中 zone |
| `GET /api/zone/{id}` | 按 ID 查询 zone 详情 |

所有端点返回 JSON，非 200 响应或连接异常时，尝试下一端口或告知用户重新打开 Tracy Profiler。
