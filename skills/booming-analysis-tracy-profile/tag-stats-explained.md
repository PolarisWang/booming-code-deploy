# Tracy Tag 统计原理详解

本文基于源码（`stats/src/stats/profile_tag.cpp` 和 `tag_stats_processor.cpp`）逐步解释 Tracy Tag 统计的完整逻辑。

---

## 1. 什么是 Tag

Tracy 中每个 Zone（插桩区间）在插桩时可以附带一个**颜色值（color）**。这个颜色值不是普通的 UI 颜色，而是一个**经过位编码的 Tag 标识符**，用于表达该 Zone 属于哪个功能模块及其在层级中的深度。

**Tag 的核心约定：**
- Zone 的 `srcloc.color` 字段（`uint32_t`，Tracy 内部为 BGR 格式）承载 Tag 信息
- `ProfileTag::getColorName(color)` 将颜色值映射为 Tag 名称字符串（如 `"logic"`, `"logic_motor"`）
- 颜色值为 0 或不在映射表中的 Zone 为**无标记 Zone**

---

## 2. Tag 的层级编码（颜色位协议）

源文件：`profile_tag.h`

颜色值（RGB 格式，24 位有效）使用如下位域分配：

```
Bit 23-14: BASE  (10 bits) — 顶层类别标识（如 logic / present / render）
Bit 13-11: L1    ( 3 bits) — 第 1 级子类别
Bit 10-6 : L2    ( 5 bits) — 第 2 级子类别
Bit  5-3 : L3    ( 3 bits) — 第 3 级子类别
Bit  2-0 : L4    ( 3 bits) — 第 4 级子类别
```

**重要：Tracy 内部存储为 BGR 格式**（字节顺序 Blue-Green-Red），但层级判断时统一转换为 RGB 进行计算。

### 层级判断逻辑（`getLevel`）

```
L4 ≠ 0 → level 4
L3 ≠ 0 → level 3
L2 ≠ 0 → level 2
L1 ≠ 0 → level 1
否则    → level 0（纯根节点）
```

### 父子关系判断（`isChildOf`）

`isChildOf(parentBgr, childBgr)` 返回 true 的条件：
1. child 与 parent 共享相同的 BASE + L1 位（同属一棵子树）
2. 若 parent 有 L2，child 的 L2 也必须匹配（相同路径前缀）
3. child 的层级深度必须大于 parent

**示例（RGB 格式）：**
```
logic            = 0x3F0800  → BASE=固定值, L1=1, L2=0, L3=0, L4=0  → level 1
logic_motor      = 0x3F0803  → BASE=同,     L1=1, L2=0, L3=0, L4=3  → level? ...
```

实际映射表（BGR格式，来自 `profile_tag.cpp`）：
```
0x00c80f → "logic"
0xc0ca0f → "logic_motor"
0xc8ca0f → "logic_motor_managertick"
0xd0ca0f → "logic_motor_imulatemovements"
0x0018a8 → "render"
0x4018a8 → "render_prerender"
0x00d0ff → "present"
```

Tag 名称中的 `_` 分隔符与颜色位层级**一一对应**：`logic_motor_managertick` 是 `logic_motor` 的子节点，是 `logic` 的孙节点。

---

## 3. 线程过滤

源码：`tag_stats_processor.cpp` 构造函数

**只统计特定线程前缀的 Zone：**
```cpp
static const char* k_allowed_thread_prefixes[] = { "Main thread", "TaskWorker", nullptr };
```

线程名以 `"Main thread"` 或 `"TaskWorker"` 开头的线程才会被纳入 Tag 统计。其他线程（如渲染线程、I/O 线程）的 Zone 会被跳过。

---

## 4. 帧边界处理

```cpp
const size_t frameCount = m_frame_data.frames.size();
m_frame_end_idx = frameCount - 1;  // 忽略最后 1 帧
// k_frame_begin_idx = 2（忽略前 2 帧）
const size_t validFrameCount = m_frame_end_idx - k_frame_begin_idx;
```

**有效帧数 = 总帧数 - 3**（首 2 帧 + 末 1 帧被忽略，避免边界帧数据不完整导致统计异常）。

这就是为什么 `stats_frame_tags` 返回的数组长度比 `frame_count` 少 3。

---

## 5. 四个核心统计量的计算

### 5.1 `self_times`（自身耗时）

**定义：** 该 Tag Zone 自身占用的时间，**不含不同 Tag 的子 Zone 耗时**，但**透明穿透无 Tag 子 Zone**。

**算法（`getSelfTime` 函数）：**

```
对于一个 Zone（属于 tag A）：

totalTime = zone.End - zone.Start

递归遍历所有子孙 Zone：
  - 子 Zone 有相同 Tag（或 zone 名匹配父 Tag 名）→ children_time += 子 Zone 时长
  - 子 Zone 有不同 Tag                          → children_time += 子 Zone 时长（截止，不再递归）
  - 子 Zone 无 Tag（透明 Zone）                 → 不计入 children_time，继续向下递归

self_time = totalTime - children_time
```

**关键设计：透明 Zone 的处理**

无 Tag 的中间 Zone（如纯粹的函数调用层）被"穿透"——它的时间被上层 Tag 所吸收，不会隔断时间归属。这样即使代码中有大量没有 Tag 的中间函数层，Tag 的 self_time 仍能准确反映该模块真实消耗的 CPU 时间。

### 5.2 `all_times`（全量耗时）

**定义：** 按 Tag 树形结构向上聚合。公式：

```
all(A) = self(A) + all(A1) + all(A2) + ...
```
其中 A1、A2 是 A 的**直接子 Tag**（通过 `getParent` 验证直接父子关系）。

**算法（`getAllTime` 函数）：**
1. 从当前 Tag 的 `self_time` 开始
2. 遍历所有 Tag，找到满足以下条件的直接子 Tag：
   - `isSameSubtree(parent, child)` 为 true（同属一棵大树）
   - `isChildOf(parent, child)` 为 true（是后代）
   - `getParent(child) == parent`（是直接子节点，不是孙节点）
3. 递归累加每个直接子 Tag 的 `all_time`

**示例：**
```
all(logic_motor) = self(logic_motor)
                 + all(logic_motor_managertick)
                 + all(logic_motor_imulatemovements)
                 + all(logic_motor_posttick)
```

### 5.3 `span_times`（多线程跨度时间）

**定义：** 该 Tag（含其所有子 Tag）在某一帧内，**从最早开始到最晚结束的时间跨度**（wall-clock 时间），而非累计 CPU 时间。

**算法（`computeSpanAndIdleTime`）：**
1. 收集该 Tag 及其所有子 Tag 在当前帧的所有时间片段（`ZoneFragment`）
2. 对所有片段排序、合并重叠
3. `span_time = latest_end - earliest_begin`

**意义：** span_time 反映该 Tag 占据的实际"墙钟时间窗口"。若多线程并行执行，span_time < all_time（多个线程在同一时间窗口内并行执行）；若单线程串行，span_time ≈ self_time。

### 5.4 `idle_times` 和 `idle_ratios`（空闲时间与空闲率）

**定义：** 在 span_time 窗口内，没有任何该 Tag（或子 Tag）Zone 在执行的空白时间。

**算法：**
```
occupied_time = 所有时间片段合并后的总执行时间
idle_time = span_time - occupied_time
idle_ratio = idle_time / span_time
```

**意义：** idle_ratio 高（> 20%）表示该 Tag 的跨度时间窗内有大量 CPU 空闲，通常意味着：
- 任务调度不均（部分 Worker 等待）
- 线程同步等待（锁竞争、join 等待）
- 该 Tag 实际并发度低

---

## 6. `undefined` 和 `all` 特殊 Tag

### `all`
- 累积所有 Zone 的**独占自身时间**（`getExclusiveSelfTime`，即 zone 时长减去所有直接子 zone 时长）
- 代表所有被 Tracy 追踪的 CPU 时间总和
- `all_time[i] = self_time[i]`（无层级聚合，直接等于自身）

### `undefined`
- 表示**没有 Tag 标记的 CPU 时间**
- 计算方式：残差法，避免双重计数

```
undefined_self[frame] = all_self[frame] - Σ(tagged_self[frame] for all tags)
```

**设计意图：** 有 Tag 的 Zone 的 `getSelfTime` 会透明穿透无 Tag 子 Zone（吸收其时间），因此直接累加无 Tag Zone 的时间会导致重复计数。用残差法可精确得出真正"无 Tag 覆盖"的 CPU 时间。

---

## 7. `parallel_ratios`（并行度）

```
parallel_ratio = all_time / (span_time - idle_time)
```

**含义：** 在有效执行时间（span_time 减去空闲时间）内，平均有多少线程在同时执行该 Tag 的 Zone。

- `parallel_ratio ≈ 1.0`：基本单线程执行
- `parallel_ratio > 1.0`：有多线程并行（如 4 个 Worker 同时跑）
- 值为 `-1.0`：该帧 span_time = 0（无数据），无效

---

## 8. 完整数据流

```
Zone 插桩（srcloc.color 编码 Tag）
  ↓
TagStatsProcessor 构造：
  1. 扫描所有 source location zones，筛选有 Tag 的 zones
  2. 线程过滤（只保留 Main thread / TaskWorker）
  3. 初始化 stats_map（含 undefined / all 占位）
  ↓
逐帧处理（getResult 主循环）：
  每帧：
    1. 遍历所有已选 source location zones
    2. 对每个 zone，按帧时间范围过滤（lower_bound + 线程过滤）
    3. 计算 self_time（透明穿透无 Tag 子 Zone）
    4. 计算 exclusiveSelfTime（用于 all / undefined）
    5. 收集时间片段（getTagFrags，用于 span/idle 计算）
    6. 计算 undefined = all - sum(tagged_self)
    7. 计算每个 Tag 的 all_time（递归树聚合）
    8. 计算 span_time 和 idle_time（computeSpanAndIdleTime）
    9. 计算 parallel_ratio 和 idle_ratio
  ↓
序列化为 JSON 数组（stats_frame_tags API 返回）
```

---

## 9. 使用注意事项

### 数组长度
`self_times`、`all_times` 等数组的长度 = **有效帧数**（= 总帧数 - 3），而非总帧数。分析时注意对齐帧索引（从 `k_frame_begin_idx = 2` 开始）。

### `all_times` vs `span_times` 的区别
| 字段 | 代表 | 单线程情况 | 多线程情况 |
|------|------|-----------|-----------|
| `self_times` | 模块自身纯 CPU 消耗（不含子 Tag） | 单帧内该 Tag 占用的 CPU cycles | 同左 |
| `all_times` | 模块含子模块总 CPU 消耗（树聚合） | ≈ span_times | > span_times（并行时） |
| `span_times` | 模块占据的墙钟时间窗 | ≈ all_times | < all_times（并行时） |

### 根节点识别
根节点 Tag 是 Tag 名称中**不含 `_`** 的节点（如 `logic`, `render`, `present`, `server`, `engine`）。分析时按根节点分组，总时长基准取所有根节点的 `span_time` 之和。

### Tag 树隔离
`isSameSubtree` 保证不同根节点的子树相互隔离：计算 `logic_motor` 的 `all_time` 时，不会误计入 `present_pretick` 的时间。

---

## 10. 快速参考：各字段分析意义

| 字段 | 典型分析问题 | 异常阈值 |
|------|------------|---------|
| `self_times` | 这个模块自身（不含子模块）慢在哪里？ | avg > 帧预算的 30% |
| `all_times` | 这个模块（含所有子模块）总共消耗多少？ | avg > 帧预算的 50% |
| `span_times` | 这个模块占据了多长的实际时间窗口？ | avg > 帧预算 |
| `idle_ratios` | 这个模块的多线程利用率如何？ | avg > 0.20（20%）⚠️ |
| `parallel_ratios` | 平均有几个线程在并行处理这个模块？ | < 1.5（期望值因模块而异） |

---

## 11. 通过 Tag 查询 Zone 实例（ZoneHelper）

源文件：`profiler/src/http/ZoneHelper.hpp` / `ZoneHelper.cpp`

除了聚合统计，还可以**按 Tag 名称反查具体的 Zone 实例 ID**，适合在发现某个 Tag 耗时异常后，定位到具体的执行实例。

### 11.1 颜色反查（resolveTagColor）

`getZoneIdsByTag` 的第一步是把 Tag 名称（字符串）反查为 BGR 颜色值：

```cpp
static uint32_t resolveTagColor(const char* tagName) {
    for (const auto& [color, name] : ProfileTag::getAllTags())
        if (std::strcmp(name, tagName) == 0) return color;
    return 0;  // 未知 tag → 返回空结果
}
```

这是 `getColorName(color)` 的逆操作，遍历全部已注册 tag 做字符串匹配。

### 11.2 时间范围转换（frameToTimeBegin / frameToTimeEnd）

帧索引过滤先转换为纳秒时间戳：

```
tMin = worker.GetFrameBegin(frames, startFrame)   // 帧开始时间
tMax = worker.GetFrameEnd(frames, endFrame)        // 帧结束时间
```

`startFrame = -1` 时 `tMin = -1`（无下界），`endFrame = -1` 时 `tMax = -1`（无上界）。

### 11.3 多线程迭代收集（collectZonesByColor）

对每个线程的 zone 树做深度优先遍历（非递归，用显式栈）：

```
对每个 zone：
  if zone.Start() > tMax → break（同层后续 zone 更晚，剪枝）
  if zone.End() < tMin  → continue（跳过）
  if zone.srcloc.color == targetColor → 收录 zone_id
  if zone.HasChildren() → 将子树入栈继续遍历
```

**关键剪枝：** 同一层级的 zone 按时间排序存储，一旦发现 `zone.Start() > tMax` 即可终止当前层扫描，显著减少无效访问。

返回的 `zone_id` 是 `reinterpret_cast<uint64_t>(ZoneEvent*)` —— 即 ZoneEvent 在内存中的地址，与 `zone <id>` API 使用的 ID 格式完全一致。

### 11.4 API 使用示例

```bash
# 查询所有 logic_motor zone 的 ID
python .claude/script/tracy/tracy_http.py zones_by_tag logic_motor

# 只查第 10~20 帧内的 zone
python .claude/script/tracy/tracy_http.py zones_by_tag logic_motor 10 20

# 对某个 zone_id 做详情查询
python .claude/script/tracy/tracy_http.py zone 140234567890

# 查该 zone 的帧号
python .claude/script/tracy/tracy_http.py frame_number 8347291000
```

### 11.5 getBelongingTag：推断无标记 Zone 的所属 Tag

对于没有直接 Tag 的 zone（srcloc.color == 0 或不在映射表中），`getBelongingTag` 会向上遍历祖先，找到最近的有 Tag 祖先的颜色：

```
ancestors = getZoneAncestors(worker, zone, threadId)
// 从 root → parent，取最近祖先的 Tag
for ancestor in reversed(ancestors):
    color = srcloc[ancestor].color
    if ProfileTag::getColorName(color) 有效: return color
return ""
```

这用于 `/api/zone/{id}` 中填充 `tag` 字段：即便 zone 自身没有 Tag，也能显示它所属的最近父 Tag 名称（方便理解该 zone 属于哪个功能模块）。

### 11.6 getFrameNumber：时间戳 → 帧编号

二分查找帧数组，找到包含该时间戳的帧：

```
lo=0, hi=total_frames
while lo < hi:
    mid = (lo + hi) / 2
    if GetFrameBegin(mid) <= timestamp: lo = mid + 1
    else: hi = mid
return lo > 0 ? lo - 1 : -1
```

返回 `-1` 表示时间戳早于第一帧开始，或 trace 无帧数据。

---

## 12. 内存池分析（analyze_memory.py）

脚本路径：`.claude/script/tracy/analyze_memory.py`

### 12.1 命令速查

| 命令 | 用途 |
|------|------|
| `python analyze_memory.py` | 全部池的 overview 摘要表 |
| `python analyze_memory.py --pool PoolDefault` | 只看指定池的摘要 |
| `python analyze_memory.py --pool PoolDefault --leak-detail` | 指定池的泄漏线程/时间分布详情 |
| `python analyze_memory.py --pool PoolDefault --freed-lifetime` | 指定池的已释放大块生命周期 |
| `python analyze_memory.py --json` | 输出原始 JSON（供后续脚本解析） |

### 12.2 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--pool <name>` | （全部） | 按名称过滤内存池，支持子串匹配 |
| `--leak-detail` | 关 | 对 `--pool` 指定的池输出泄漏线程/时间分布，需配合 `--pool` |
| `--freed-lifetime` | 关 | 对 `--pool` 指定的池分析已释放大块的 alloc→free 时长 |
| `--min-size-mb <n>` | 50 | `--freed-lifetime` 时的最小块大小（MB） |
| `--sample <n>` | 500 | `--leak-detail` / `--freed-lifetime` 的采样条数（按 size 降序） |
| `--bucket <s>` | 20 | `--leak-detail` 时间分桶宽度（秒） |
| `--json` | 关 | 输出原始 JSON（仅 overview 模式） |

### 12.3 输出说明

**overview 摘要表字段：**

| 字段 | 含义 | 异常阈值 |
|------|------|---------|
| 总分配次 | 全程 alloc 调用次数 | — |
| 总分配量 | 全程分配字节总量 | — |
| 存活次 | 未释放的分配个数 | — |
| 存活量 | 未释放的字节总量 | — |
| 存活率 | `active_count / alloc_count` | **> 1%** 标注 ⚠️ 疑似泄漏 |
| 备注 | 频繁分配 | **> 50次/帧** 标注频繁分配 |

**`--leak-detail` 附加输出三段：**

1. **泄漏按线程分组** — 各线程的泄漏块数、总大小，每线程展示前 3 个最大块及其出现时间
2. **泄漏时间分布** — 按 `--bucket` 秒分桶，直观看泄漏集中在哪个时段（启动？场景切换？运行中？）
3. **最大泄漏块 Top10** — 按 size 降序，附带出现时间和线程名

**`--freed-lifetime` 附加输出：**

- 已释放的大块（`> --min-size-mb`），显示 alloc 时间、free 时间、持续时长
- 用于判断大块内存是短暂 spike（lifetime < 1s）还是长期持有（lifecycle 贯穿整个场景）

### 12.4 典型分析流程

**Step 1 — 全局扫描，找异常池：**
```bash
python .claude/script/tracy/analyze_memory.py
```
看 `存活率 > 10%` 且 `存活量 > 100MB` 的池，优先排查。

**Step 2 — 定位泄漏来源线程和时段：**
```bash
python .claude/script/tracy/analyze_memory.py --pool PoolDefault --leak-detail
```
关注：
- 哪个线程贡献了最多泄漏量？（通常是 Main thread 或特定 TaskWorker）
- 泄漏集中在哪个时间桶？（t=0 启动期 vs 运行中持续增长）

**Step 3 — 判断大块是否是正常的 slab：**
```bash
python .claude/script/tracy/analyze_memory.py --pool PoolDefault --freed-lifetime --min-size-mb 100
```
若 lifetime 贯穿整个 trace（>= trace 总时长的 80%），通常是子池向父池申请的 slab（正常行为）。
若 lifetime 很短（< 10s）但未释放，则是真正泄漏。

**Step 4 — JSON 格式供 AI 解析：**
```bash
python .claude/script/tracy/analyze_memory.py --json | python -c "
import json, sys
data = json.load(sys.stdin)
# 找存活率 > 10% 的池
leaked = [r for r in data if r['survive_rate'] > 0.10]
for r in sorted(leaked, key=lambda x: -x['active_bytes']):
    print(r['pool'], r['active_bytes']//1024//1024, 'MB', f\"{r['survive_rate']*100:.1f}%\")
"
```

### 12.5 常见误报识别

| 现象 | 原因 | 是否真正泄漏 |
|------|------|------------|
| PoolDefault 存活率 17%，存活 3GB | 40 个子池从 PoolDefault 申请 slab，进程生命周期内不归还 | **否** — 正常 slab 行为 |
| AnimationTreePool 存活率 100% | 该池初始化后从未有对象被 Destroy | **是** — 检查对应系统 Shutdown 逻辑 |
| CameraPool 存活率 100%，2.3MB | 摄像机对象从不释放 | **是** — 检查 Camera Destroy 流程 |
| PhysicsPool 存活率 48.8%，1.8GB | 物理对象随场景/角色销毁时未调用对应的 Free | **是** — P0 问题 |
| DatumTablePool 存活率 98.7% | 数据表在 trace 期间几乎不回收 | **是** — 检查 DatumTable 生命周期管理 |
