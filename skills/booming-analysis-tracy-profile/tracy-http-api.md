# Tracy HTTP API 能力参考

Tracy Profiler UI 嵌入了一个 HTTP 服务器（端口 9090-9099），通过 `tracy_http.py` 脚本调用。

## 脚本调用方式

所有命令均通过以下方式执行（在项目根目录）：

```bash
python .claude/script/tracy/tracy_http.py <命令> [参数...]
```

**通用行为：**
- 自动扫描 9090-9099，找到第一个已加载 trace 的实例
- 成功时 exit code 0，输出 JSON（含 `port` 字段）
- 失败时 exit code 1，输出 `{"error": "..."}`
- 端口扫描超时 1.0s/端口，API 查询超时 5.0s

---

## 命令速查

### 连接与基础

| 命令 | 说明 | 关键返回字段 |
|------|------|-------------|
| `filepath` | 找到已加载 trace 的实例，返回文件路径和端口 | `filepath`, `port` |
| `trace_overview` | trace 全局摘要：程序名、主机、时间范围、各类计数 | `captured_program`, `host_info`, `first_time`, `last_time`, `zone_count`, `frame_count`, `message_count`, `plot_count`, `context_switch_count` |
| `stats_summary` | trace 聚合摘要，同 trace_overview 并额外含 `lock_count` | `captured_program`, `host_info`, `first_time`, `last_time`, `zone_count`, `frame_count`, `lock_count`, `plot_count`, `message_count`, `context_switch_count` |
| `trace_info` | trace 完整详细信息（见下方详细说明） | `host`, `cpu`, `timing`, `app_info`, `cpu_topology`, `frame_stats`, `trace_stats` |

#### `trace_info` 返回格式

返回单个 JSON 对象，包含以下段：

```json
{
  "host": "Windows 11 Pro, i9-13900K, 64GB",
  "cpu": {
    "manufacturer": "GenuineIntel",
    "cpu_id": "0x000906A4",
    "architecture": "x86_64"
  },
  "timing": {
    "capture_time": 1700000000,
    "executable_time": 1700000001,
    "delay_ns": 14000,
    "resolution_ns": 100,
    "pid": 12345
  },
  "app_info": [
    "GameVersion=1.2.3",
    "BuildConfig=Release"
  ],
  "cpu_topology": {
    "pkg_0": {
      "die_0": {
        "core_0": [0, 1],
        "core_1": [2, 3]
      }
    }
  },
  "frame_stats": {
    "total_frames": 1247,
    "first_time_ns": 0,
    "last_time_ns": 20800000000,
    "total_time_ns": 20800000000,
    "min_frame_ns": 12000000,
    "max_frame_ns": 83200000,
    "avg_frame_ns": 16679231
  },
  "trace_stats": {
    "zone_count": 2300000,
    "gpu_zone_count": 450000,
    "lock_count": 128,
    "plot_count": 4,
    "message_count": 512,
    "context_switch_count": 127000,
    "callstack_sample_count": 89000,
    "src_loc_count": 3200,
    "symbol_count": 8500,
    "thread_count": 8
  }
}
```

| 段 | 说明 |
|----|------|
| `host` | 主机信息字符串（OS 版本、机器名等） |
| `cpu.manufacturer` | CPU 厂商字符串（"GenuineIntel" / "AuthenticAMD"） |
| `cpu.cpu_id` | CPU ID 十六进制（家族/型号/步进编码） |
| `cpu.architecture` | 架构：`x86` / `x86_64` / `arm32` / `arm64` / `Unknown` |
| `timing.capture_time` | 抓取开始时间（Unix 时间戳，秒） |
| `timing.executable_time` | 可执行文件修改时间（Unix 时间戳，秒） |
| `timing.delay_ns` | 采样延迟（纳秒） |
| `timing.resolution_ns` | 时钟分辨率（纳秒） |
| `timing.pid` | 被采样进程 PID |
| `app_info` | 应用自定义信息数组（通过 TracyAppInfo 写入的 key=value 行） |
| `cpu_topology` | CPU 拓扑：`pkg → die → core → [thread_id, ...]` |
| `frame_stats.total_frames` | 总帧数 |
| `frame_stats.{min/max/avg}_frame_ns` | 帧时长统计（纳秒） |
| `trace_stats.zone_count` | zone 总数 |
| `trace_stats.gpu_zone_count` | GPU zone 总数 |
| `trace_stats.callstack_sample_count` | 调用栈采样数 |
| `trace_stats.src_loc_count` | 源码位置数 |
| `trace_stats.thread_count` | 线程数 |

### Zone 查询

| 命令 | 说明 | 关键返回字段 |
|------|------|-------------|
| `selection` | 读取 UI 当前选中 zone | `valid`, `zone_id`, `name`, `function`, `file`, `line`, `thread_id`, `thread_name`, `parent_id`, `children_ids`, `start_ns`, `duration_ns`, `tag`, `frame_number` |
| `zone <id>` | 按 zone_id 查询 zone 详情（与 selection 字段相同） | 同上 |
| `zone_children <id>` | 获取指定 zone 的直接子 zone 列表 | `children: [{zone_id, function, file, line, duration_ns, ...}]` |
| `zones_by_tag <tag> [start_frame] [end_frame]` | 按 Tag 名称查询所有匹配 zone 的 ID 列表，可按帧范围过滤 | `tag`, `count`, `zone_ids: [uint64, ...]` |

#### `zones_by_tag` 详细说明

```bash
# 查询所有 logic_motor tag 的 zone ID
python .claude/script/tracy/tracy_http.py zones_by_tag logic_motor

# 只查询第 10~20 帧内的 zone
python .claude/script/tracy/tracy_http.py zones_by_tag logic_motor 10 20
```

返回格式：
```json
{
  "tag":      "logic_motor",
  "count":    42,
  "zone_ids": [140234567890, 140234567912, ...]
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `tag` | string | Tag 名称，必须与 `profile_tag.cpp` 中的映射完全一致（如 `logic_motor`） |
| `start_frame` | int（可选） | 起始帧索引（0-based，包含）；省略或 -1 表示无下界 |
| `end_frame` | int（可选） | 结束帧索引（0-based，包含）；省略或 -1 表示无上界 |

返回的 `zone_ids` 是 `ZoneEvent*` 指针地址，可直接传给 `zone <id>` 或 `zone_children <id>` 做进一步查询。

**注意：**
- Tag 名称未知（不在映射表中）时返回 `count: 0, zone_ids: []`，不报错
- 跨越帧边界的 zone（start 在帧内但 end 超出）仍会被收录

### 线程与帧

| 命令 | 说明 | 关键返回字段 |
|------|------|-------------|
| `threads` | 所有线程列表 | `threads: [{thread_id, thread_name}]` |
| `frames [offset] [count]` | 分页帧列表，默认 0 100，上限 1000/次 | `total_count`, `frames: [{frame_idx, start_ns, end_ns, duration_ns}]` |
| `frame_number <ts_ns>` | 将时间戳（纳秒）转换为帧编号 | `ts_ns`, `frame_number` |
| `stats_export_csv` | 帧统计 CSV（输出原始文本，非 JSON） | 列：`frame`, `time_from_start`, `frame_duration`, `frame_start_time`, `frame_end_time`（时间单位 ms） |

#### `frame_number` 详细说明

```bash
# 查询时间戳 1234567890 ns 对应的帧编号
python .claude/script/tracy/tracy_http.py frame_number 1234567890
```

返回格式：
```json
{
  "ts_ns":        1234567890,
  "frame_number": 73
}
```

`frame_number` 为 `-1` 表示该时间戳不在任何帧范围内（或 trace 无帧数据）。

**典型用途：** 结合 `zones_by_tag` 查到某个 zone 的 `start_ns`，再用 `frame_number` 确认它属于哪一帧：

```bash
# 1. 查 logic_motor 的所有 zone
python .claude/script/tracy/tracy_http.py zones_by_tag logic_motor

# 2. 取某个 zone_id 查详情，得到 start_ns
python .claude/script/tracy/tracy_http.py zone 140234567890

# 3. 用 start_ns 查帧编号
python .claude/script/tracy/tracy_http.py frame_number 8347291000

### 消息

| 命令 | 说明 | 关键返回字段 |
|------|------|-------------|
| `messages [offset] [count] [start_ns] [end_ns]` | 分页消息，支持时间范围，上限 500/次 | `total_count`, `messages: [{time, text, thread_id, thread_name, color}]` |

### Plot（绘图）

| 命令 | 说明 | 关键返回字段 |
|------|------|-------------|
| `plots` | 所有 plot 名称列表 | `plots: [string]` |
| `plot_count <name>` | 指定 plot 的采样点数 | `count: int` |
| `plot_values <name> [offset] [count] [start_ns] [end_ns]` | 分页采样值，上限 1000/次 | `total_count`, `values: [{time, val}]` |

### 内存池

| 命令 | 说明 | 关键返回字段 |
|------|------|-------------|
| `pools` | 所有内存池名称 | `pools: [string]` |
| `pool_overview <pool> <start_ns> <end_ns>` | 时间范围内内存概况（start/end 必填） | `alloc_count`, `free_count`, `alloc_bytes`, `free_bytes`, `active_count`, `active_bytes` |
| `pool_allocations <pool> <start_ns> <end_ns> [offset] [count] [sort]` | 分配详情，sort: none/size_descend/size_ascend/appeared_at_descend/appeared_at_ascend | `allocations: [{address, size, appeared_at, is_freed, free_time, thread_alloc_id, thread_free_id}]` |
| `pool_callstack_tree <pool> <include_active> <include_inactive> [start_ns] [end_ns]` | 自下而上调用栈树根节点 | `roots: [{frame_name, file, line, alloc_count, alloc_bytes, child_count}]` |

### CPU Tag 统计

| 命令 | 说明 | 关键返回字段 |
|------|------|-------------|
| `stats_frame_tags` | 按 Profiler Tag 分解的逐帧耗时统计 | 见下方详细说明 |

#### `stats_frame_tags` 返回格式

返回 JSON 数组，每项对应一个 Tag：

```json
[
  {
    "tag_name": "logic",
    "self_times":       [1000000, 1200000, ...],
    "all_times":        [2000000, 2100000, ...],
    "span_times":       [1500000, 1800000, ...],
    "parallel_ratios":  [0.75, 0.83, ...],
    "idle_times":       [200000, 150000, ...],
    "idle_ratios":      [0.13, 0.08, ...]
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `tag_name` | string | Tag 名称（对应 Tracy srcloc.color 编码的层级名） |
| `self_times` | int64[] | 每帧该 Tag 自身耗时（纳秒），不含子 Tag 耗时 |
| `all_times` | int64[] | 每帧该 Tag 全量耗时（含子 Tag）：`all = self + child1_all + child2_all + ...` |
| `span_times` | int64[] | 每帧多线程跨度时间（最晚结束 - 最早开始，纳秒） |
| `parallel_ratios` | float[] | 每帧并行度：`all_time / (span_time - idle_time)`，无效时为 `-1.0` |
| `idle_times` | int64[] | 每帧跨度内无 zone 执行的空闲时间（纳秒） |
| `idle_ratios` | float[] | 每帧空闲率：`idle_time / span_time`，无效时为 `-1.0` |

**注意：**
- 数组长度 = 有效帧数（忽略首尾各 1-3 个边界帧）
- `parallel_ratios` 和 `idle_ratios` 值为 `-1.0` 表示该帧无多线程数据（span_time = 0）
- Tag 层级关系由 `srcloc.color` 的位编码决定，`all_times` 按树形向上聚合

---

## 错误处理

| 情形 | 返回 | exit code |
|------|------|-----------|
| 端口均无响应或无已加载文件 | `{"error": "Tracy Profiler UI not found..."}` | 1 |
| HTTP 错误（404 等） | `{"error": "HTTP 404: Not Found"}` | 1 |
| 无 trace 加载（503 接口） | `{"error": "No trace loaded"}` | 1 |
| 成功 | 正常 JSON + `port` 字段 | 0 |

**503 接口**（无 trace 时返回 503）：`trace_overview`, `trace_info`, `threads`, `frames`, `messages`, `plots`, `plot_count`, `plot_values`, `pools`, `pool_overview`, `pool_allocations`, `pool_callstack_tree`, `stats_summary`, `stats_frame_tags`, `stats_export_csv`, `zones_by_tag`, `frame_number`

---

## 常用分析脚本

在 `.claude/script/tracy/` 目录下提供了以下高层分析脚本，封装了常见的性能分析逻辑，可直接调用。

### 脚本速查

| 脚本文件 | 用途 | 典型用途 |
|---------|------|---------|
| `analyze_overview.py` | Trace 全局概况 | 分析开始时建立基础认知 |
| `analyze_frames.py` | 帧率统计与最差帧查找 | 帧率问题 / 卡顿分析 |
| `analyze_tags.py` | CPU Tag 层级耗时分析 | 整体瓶颈定位 |
| `analyze_memory.py` | 内存池分配与泄漏统计 | 内存问题分析 |

---

### `analyze_overview.py` — Trace 概况

一键输出程序信息、帧率摘要、线程 / Plot / 内存池列表，适合作为任何分析的第一步。

```bash
# 文字摘要（推荐）
python .claude/script/tracy/analyze_overview.py

# JSON 格式（可供后续脚本解析）
python .claude/script/tracy/analyze_overview.py --json
```

**典型输出：**
```
=== Trace 基础信息 ===
程序：game.exe
主机：Windows 11 Pro, i9-13900K
PID：12345   时钟精度：100 ns
App Info：GameVersion=1.2.3 / BuildConfig=Release
CPU：1 个 Package，共 16 个逻辑核

=== Trace 时长与规模 ===
时长：20.84s   帧数：1,247
Zone 总数：2,300,000   消息：512   锁：128   Plot：4

=== 帧率概况（来自 trace_info）===
平均帧时：16.7ms（59.9 FPS）
最差帧：83.2ms   最优帧：12.0ms

=== 线程列表（共 8 个）===
  [12345] Main thread
  [12346] TaskWorker_0
  ...
```

---

### `analyze_frames.py` — 帧率统计

获取全量帧数据，计算超预算帧数、百分位数、最差 N 帧。

```bash
# 默认预算 16.67ms（60FPS），显示最差5帧
python .claude/script/tracy/analyze_frames.py

# 自定义帧预算和显示数量
python .claude/script/tracy/analyze_frames.py --budget 33.33 --top 10

# JSON 格式输出（供 AI 解析）
python .claude/script/tracy/analyze_frames.py --json
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--budget <ms>` | 帧时间预算（毫秒） | `16.67`（60FPS） |
| `--top <n>` | 显示最差 N 帧 | `5` |
| `--json` | 输出 JSON | 否 |

**典型输出：**
```
=== 帧率统计（共 1,247 帧，总时长 20.8s）===
平均帧时：16.7ms（59.9 FPS）
最差帧：第 847 帧，83.2ms（超预算 4.9×）
最优帧：12.0ms

超预算帧（> 16.67ms = 60FPS）：187 帧（15.0%）  ⚠️
超 2× 预算帧（> 33.33ms）：23 帧

百分位：
  P50=15.1ms  P75=17.4ms  P90=21.2ms  P99=48.6ms

最差 5 帧：
  #847    83.2ms  [+4.9×]  ⚠️
  #203    61.4ms  [+3.7×]  ⚠️
  #901    58.7ms  [+3.5×]  ⚠️
  #156    47.3ms  [+2.8×]  ⚠️
  #512    42.1ms  [+2.5×]  ⚠️
```

---

### `analyze_tags.py` — CPU Tag 耗时分析

从 `stats_frame_tags` 数据中计算各 Tag 的全程累计耗时和平均每帧耗时，按层级树形展示。

```bash
# 全量层级展示
python .claude/script/tracy/analyze_tags.py

# 只看 logic 子树
python .claude/script/tracy/analyze_tags.py --filter logic

# JSON 格式（每个 tag 的聚合数据）
python .claude/script/tracy/analyze_tags.py --json
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--filter <prefix>` | 只显示指定前缀的 tag | 全部 |
| `--json` | 输出 JSON | 否 |

**典型输出：**
```
=== CPU Tag 耗时分析（全程 20.8s，1,245 帧）===
Tag                                               总span     占比   avg/帧    空闲率
------------------------------------------------------------------------------------------
▼ logic                                          12,400.0ms  59.6%  avg/frame:  9.96ms
  ▼ logic_motor                                   6,200.0ms  29.8%  avg/frame:  4.98ms
      logic_motor_managertick                     2,100.0ms  10.1%  avg/frame:  1.69ms
  ▼ logic_physicsscene                            3,800.0ms  18.3%  avg/frame:  3.05ms
      logic_physicsscene_simulate                 2,400.0ms  11.5%  avg/frame:  1.93ms

▼ present                                         5,200.0ms  25.0%  avg/frame:  4.18ms   idle: 22% ⚠️多线程利用率低
    present_animation                             2,100.0ms  10.1%  avg/frame:  1.69ms

▼ render                                          2,800.0ms  13.5%  avg/frame:  2.25ms
```

**异常标注规则：**
- `⚠️多线程利用率低`：avg idle_ratio > 20%，表示该 tag 跨度时间内有大量空闲，多线程未充分利用
- `← 主要瓶颈`：span_time 占总时长 > 50%

---

### `analyze_memory.py` — 内存池分析

对所有内存池执行全程 overview，统计分配次数、存活量，标注疑似泄漏。

```bash
# 分析所有内存池
python .claude/script/tracy/analyze_memory.py

# 只分析 default 池
python .claude/script/tracy/analyze_memory.py --pool default

# JSON 格式
python .claude/script/tracy/analyze_memory.py --json
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--pool <name>` | 只分析指定内存池 | 全部 |
| `--json` | 输出 JSON | 否 |

**典型输出：**
```
=== 内存池摘要（trace 全程 20.8s，1,247 帧）===
池名                            总分配次      总分配量    存活次     存活量        存活率  备注
--------------------------------------------------------------------------------------------------------------
default                            4,821      1.20 GB        23      19.6 MB     0.5%  ⚠️ 疑似泄漏
temp                              98,432      2.10 GB         0         0 B      0.0%  频繁分配 79次/帧
gpu                                  312    380.0 MB          0         0 B      0.0%  ✓
--------------------------------------------------------------------------------------------------------------
总存活内存：19.6 MB
```

**异常标注规则：**
- 存活率 > 1%：`⚠️ 疑似泄漏`（分配后未释放比例高）
- 分配次/帧 > 50：`频繁分配 N次/帧`（GC 压力风险）

---

### 脚本组合使用示例

**快速建立全局认知（分析开始时）：**
```bash
python .claude/script/tracy/analyze_overview.py
python .claude/script/tracy/analyze_frames.py
python .claude/script/tracy/analyze_tags.py
```

**定位帧率问题：**
```bash
# 1. 找出最差帧
python .claude/script/tracy/analyze_frames.py --top 10 --json

# 2. 查最差帧区间内的消息（把 start_ns/end_ns 替换为实际值）
python .claude/script/tracy/tracy_http.py messages 0 50 <start_ns> <end_ns>
```

**分析 logic 模块瓶颈：**
```bash
python .claude/script/tracy/analyze_tags.py --filter logic
```
