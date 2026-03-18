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

### 线程与帧

| 命令 | 说明 | 关键返回字段 |
|------|------|-------------|
| `threads` | 所有线程列表 | `threads: [{thread_id, thread_name}]` |
| `frames [offset] [count]` | 分页帧列表，默认 0 100，上限 1000/次 | `total_count`, `frames: [{frame_idx, start_ns, end_ns, duration_ns}]` |
| `stats_export_csv` | 帧统计 CSV（输出原始文本，非 JSON） | 列：`frame`, `time_from_start`, `frame_duration`, `frame_start_time`, `frame_end_time`（时间单位 ms） |

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

**503 接口**（无 trace 时返回 503）：`trace_overview`, `trace_info`, `threads`, `frames`, `messages`, `plots`, `plot_count`, `plot_values`, `pools`, `pool_overview`, `pool_allocations`, `pool_callstack_tree`, `stats_summary`, `stats_frame_tags`, `stats_export_csv`
