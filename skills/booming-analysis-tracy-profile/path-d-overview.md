# 路径 D：综合概况分析

适用场景："整体"、"概况"、"哪里最慢"，或用户没有明确焦点时的入门分析。

---

## D1. 全量概况采集

并行执行所有数据采集命令：

```bash
python .claude/script/tracy/tracy_http.py trace_info
python .claude/script/tracy/tracy_http.py trace_overview
python .claude/script/tracy/tracy_http.py threads
python .claude/script/tracy/tracy_http.py frames 0 1000
python .claude/script/tracy/tracy_http.py stats_frame_tags
python .claude/script/tracy/tracy_http.py plots
python .claude/script/tracy/tracy_http.py pools
python .claude/script/tracy/tracy_http.py messages 0 500
```

内存池（如有）：

```bash
# 对每个 pool 执行
python .claude/script/tracy/tracy_http.py pool_overview <pool> <first_time_ns> <last_time_ns>
```

Plot 数据（对每个 plot 采样）：

```bash
# 对每个 plot 执行（取全量，最多1000点）
python .claude/script/tracy/tracy_http.py plot_values <plot_name> 0 1000
```

---

## D2. 分段分析与输出

按以下 6 个分析段逐一处理，全部完成后输出报告。

---

### 段 1：Trace 基础信息

从 `trace_info` 提取：

```
=== Trace 基础信息 ===

程序：game.exe（PID: 12345）
主机：Windows 11 Pro, i9-13900K（GenuineIntel / x86_64 / CPUID: 0x000906A4）
App Info：GameVersion=1.2.3 / BuildConfig=Release
时钟精度：100 ns   采样延迟：14,000 ns

CPU 拓扑：2 个 Package，每包 8 核，16 线程（HT 开启）
```

从 `trace_overview` 补充：

```
Trace 时长：20.8s（帧 0 ~ 帧 1,246）
Zone 总数：2,300,000   GPU Zone：450,000
线程数：8   锁：128   消息：512
```

---

### 段 2：帧率统计

从 `frames` 数据计算（取所有帧 duration_ns）：

```
=== 帧率统计 ===

总帧数：1,247   总时长：20.8s
平均帧时：16.7ms（59.9 FPS）
最差帧：第 847 帧，83.2ms（超预算 4.9×）

超预算帧统计：
  > 33ms（< 30 FPS）：23 帧（1.8%）
  > 16.7ms（< 60 FPS）：187 帧（15.0%）⚠️

最差 5 帧：
  #847   83.2ms  [+4.9×]
  #203   61.4ms  [+3.7×]
  #901   58.7ms  [+3.5×]
  #156   47.3ms  [+2.8×]
  #512   42.1ms  [+2.5×]
```

帧时长百分位（从排序后数组取）：
- P50（中位）/ P75 / P90 / P99

---

### 段 3：CPU Tag 耗时分析（层级展示）

从 `stats_frame_tags` 中提取所有 tag，**按 tag 名称的层级关系树形展示**。

**层级识别规则：**
- `logic` 是根节点
- `logic_motor` 是 `logic` 的子节点（名称包含父节点名称作为前缀，用 `_` 分隔）
- `logic_motor_ik` 是 `logic_motor` 的子节点
- 同理适用于 render、audio、present 等树

**计算方式：**
- 每个 tag 的全程累计 span_time = `sum(span_times)` （排除 -1.0 的无效帧）
- 总耗时基准 = 所有根节点 span_time 之和
- 显示：累计耗时（ms）、占总时长百分比、平均每帧耗时（ms）、avg idle_ratio

**输出格式（按层级缩进，同层按 span_time 降序）：**

```
=== CPU Tag 耗时分析（全程 20.8s）===

▼ logic          12.4s  60%   avg/frame: 9.9ms   idle: 8%
  ▼ logic_motor   6.2s  30%   avg/frame: 5.0ms   idle: 5%
    ▼ logic_motor_ik  2.1s  10%  avg/frame: 1.7ms
      logic_motor_ik_solve  1.8s   9%  avg/frame: 1.4ms
  ▼ logic_ai      3.8s  18%   avg/frame: 3.0ms   idle: 12%
    logic_ai_path  2.1s  10%  avg/frame: 1.7ms
  logic_net       2.4s  12%   avg/frame: 1.9ms

▼ render          5.8s  28%   avg/frame: 4.7ms   idle: 3%
  render_shadow   2.3s  11%   avg/frame: 1.8ms
  render_terrain  1.9s   9%   avg/frame: 1.5ms

▼ present         2.6s  12%   avg/frame: 2.1ms
```

**异常标注规则：**
- 某 tag avg `idle_ratio` > 20%：标注 `⚠️ 多线程利用率低`
- 某 tag 的 span_time 占总时长 > 50%：标注 `← 主要瓶颈`
- 子节点合计 > 父节点 all_time 的 90%：提示父节点自身逻辑轻量

---

### 段 4：Plot 数据统计

如果 `plots` 返回非空列表，对每个 plot 进行统计分析。

**计算方式（从 `plot_values` 的全量数据）：**
- 最小值 / 最大值 / 平均值
- 标准差（反映波动程度）
- 如值域 > 平均值 × 3，标注 `⚠️ 波动剧烈`

```
=== Plot 数据统计 ===

FPS           avg:  59.2   min: 12.0   max: 60.0   std:  4.3  ⚠️ 波动剧烈
MemUsage(MB)  avg: 846.3   min: 810.0  max: 921.0  std: 18.7
DrawCalls     avg: 1,247   min: 800    max: 2,100  std: 142    ⚠️ 波动剧烈
GPUTime(ms)   avg:  8.4    min:  3.2   max: 21.3   std:  2.1
```

如果 plot 名称含 `FPS`/`fps`：将 plot 均值与帧率统计互相印证（两者应接近）。

如果没有 plot 数据：跳过本段，说明 "此 trace 未记录 Plot 数据"。

---

### 段 5：内存池摘要

如果 `pools` 返回非空列表，对每个 pool 执行 `pool_overview`（时间范围 = trace 全程）。

**计算方式：**
- 每池：总分配次、总分配量、总释放次、存活（未释放）次、存活量
- 总内存 = 所有池 active_bytes 之和
- 若某池 active_bytes > 0：计算存活率 = active_count / alloc_count

```
=== 内存池摘要 ===

池名       总分配次    总分配量    存活次    存活量       存活率
default    4,821      1.20 GB    23        19.6 MB     0.5%   ⚠️ 有存活
gpu          312      380 MB      0           0         ✓
temp      98,432      2.10 GB     0           0         ✓（频繁分配: 79次/帧）

总存活内存：19.6 MB
```

**异常标注规则：**
- 存活率 > 1%：`⚠️ 有存活，疑似泄漏或长生命周期对象`
- 分配次数 / 帧数 > 50：`（频繁分配: N次/帧）`
- 某池 active_bytes > 总物理内存的 20%（如 trace_info 中无物理内存则跳过）：`⚠️ 内存占用高`

如果没有内存池数据：跳过本段，说明 "此 trace 未记录内存分配数据"。

---

### 段 6：加载时长分析

从全量消息（`messages 0 500`，如超过 500 条需翻页）中搜索 `Loading Status changed` 相关文本。

**匹配规则（大小写不敏感）：**
- `Loading Status changed to true` / `loading start` / `LoadingState: true` → 加载开始时间戳
- `Loading Status changed to false` / `loading end` / `LoadingState: false` → 加载结束时间戳

**可能需要翻页获取完整消息：**

```bash
python .claude/script/tracy/tracy_http.py messages 0 500
# 如 total_count > 500，继续取后续：
python .claude/script/tracy/tracy_http.py messages 500 500
```

**如果找到配对的 true/false 消息：**

```
=== 加载时长分析 ===

检测到 2 次加载周期：

  加载 #1：t=0.23s → t=3.81s   持续 3.58s   ← 初始加载
  加载 #2：t=9.12s → t=11.40s  持续 2.28s   ← 关卡切换

总加载时长：5.86s / 总时长 20.8s = 28.2%⚠️

期间帧率：N/A（通常为加载屏，帧率无意义）
```

**如果只有 true 没有 false（加载未完成）：**

```
⚠️ 检测到加载开始（t=0.23s），但未检测到加载结束，trace 可能在加载中截止。
```

**如果没有 Loading Status 消息：**
跳过本段，说明 "未检测到加载状态消息，如需分析加载时长请确认日志格式"。

---

## D3. 汇总问题，输出建议

在所有段完成后，汇总异常并按严重程度排序：

```
=== 发现的主要问题（按严重程度）===

【P0】帧级卡顿：23 帧超 33ms（最差 83ms，第 847 帧）
【P1】logic_motor_ik 耗时 10% 且无多线程加速（idle 0%），是最深的单线程热点
【P2】加载时长占比 28.2%，加载 #1 耗时 3.58s，建议分析加载期间 zone 分布
【P3】default 池存活 23 个分配（19.6 MB），需确认是否预期
【P4】FPS plot 波动剧烈（std: 4.3），与帧级卡顿一致

建议分析方向：
  [1] 深入分析最差帧 #847 → 路径 B
  [2] 分析 logic_motor_ik 的单线程热点 → 路径 A（选中该 zone）
  [3] 排查加载期间 #1（t=0.23~3.81s）的 zone 耗时 → 路径 B（帧范围过滤）
  [4] 排查 default 池 23 个存活分配 → 路径 C
```

---

## D4. 输出分析报告文件

将上述全部分析内容写入 Markdown 文件：

**路径格式：**
```
docs/booming/<YYYY-MM-DD>-<feature-name>/profile-<YYYY-MM-DD-HH>-<feature-name>.md
```

其中：
- `<feature-name>` 从 `trace_info.app_info` 提取程序名（如 `game`），或用 trace 文件名
- `<YYYY-MM-DD>` = 今天日期
- `<YYYY-MM-DD-HH>` = 今天日期 + 当前小时（两位，如 `14`）

**文件内容 = 上述所有输出段的完整 Markdown**，格式：

```markdown
# Performance Profile Report

**程序：** game.exe（PID: 12345）
**时间：** 2026-03-18 14:xx
**Trace 时长：** 20.8s，1,247 帧

---

## Trace 基础信息
[段1内容]

## 帧率统计
[段2内容]

## CPU Tag 耗时分析
[段3内容]

## Plot 数据统计
[段4内容，如无则省略]

## 内存池摘要
[段5内容，如无则省略]

## 加载时长分析
[段6内容，如无则省略]

## 问题汇总与建议
[D3内容]
```

写入文件后告知用户：

> 「分析报告已保存至 `docs/booming/2026-03-18-game/profile-2026-03-18-14-game.md`」
