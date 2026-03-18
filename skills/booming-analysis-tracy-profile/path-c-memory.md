# 路径 C：内存分析

适用场景："内存"、"泄漏"、"分配"、"OOM" 相关问题。

---

## C1. 建立基础结构认知

并行获取所有内存池和全局概况：

```bash
python .claude/script/tracy/tracy_http.py pools
python .claude/script/tracy/tracy_http.py trace_overview
python .claude/script/tracy/tracy_http.py frames 0 500   # 用于后续帧关联分析
```

向用户展示基础结构（一句话）：
```
内存池：default（通用）/ gpu（GPU 资源）/ temp（临时分配）
总帧数：1,247 帧，时长 20.8s
```

若用户描述了问题时间段（如"加载时"），从帧数据中确定对应 `start_ns/end_ns`；否则用 `first_time ~ last_time` 全程分析。

---

## C2. 各池全量概况

对每个池执行：

```bash
python .claude/script/tracy/tracy_http.py pool_overview <pool> <start_ns> <end_ns>
```

输出对比表，标注异常项：

```
内存池概况（全程 20.8s）：
  池名      总分配次    总分配量    总释放次    存活次    存活量
  default   4,821      1.2 GB     4,798      23       19.6 MB  ⚠️ 有存活
  gpu       312        380 MB     312        0        0        ✓ 全部释放
  temp      98,432     2.1 GB     98,432     0        0        ✓ 全部释放（频繁！）
```

---

## C3. 四类异常分配定位

以下四类问题独立检查，有命中则深入分析，无命中则跳过。

---

### 【异常类型 1】频繁小额分配——高频 GC 压力

**判断标准：** `temp` 池或 `default` 池的分配次数 >> 帧数（如 temp 98,432 次 ÷ 1,247 帧 = 79 次/帧），说明每帧有大量临时分配，可能引发 GC 或 allocator 竞争。

**数据采集：**

```bash
# 按时间升序取高频分配时段的 top-100，观察 appeared_at 密度
python .claude/script/tracy/tracy_http.py pool_allocations temp <start_ns> <end_ns> 0 100 appeared_at_ascend
```

分析 `appeared_at` 分布：若每帧时间窗口内有 50+ 次，标记为频繁分配问题。

**结论格式：**
```
⚠️ 【频繁分配】temp 池：98,432 次 / 1,247 帧 = 79 次/帧
  平均每次 21.8KB，峰值时段 t=8.2~9.1s（200ms 内 12,847 次）
  最可能来源：thread=RenderThread（占总次数 67%）
  → 推测：RenderThread 每帧构建临时渲染数据未复用，建议改为帧级对象池
```

---

### 【异常类型 2】分配到错误的内存池

**判断标准：** 根据池名与线程名/分配大小的匹配关系，识别"不该出现在这里"的分配。

**判断规则（通用）：**
- `gpu` 池有来自 `MainThread` 的分配 → GPU 资源应在 RenderThread 创建
- `temp` 池出现 > 10MB 的单次分配 → temp 池设计为小临时块，大分配应进 `default`
- `default` 池有来自 `AudioThread` 的高频小分配 → 音频应有独立内存池避免竞争
- 任意池出现来自 `WorkerPool` 线程的大额分配 → Worker 通常不应直接管理资产生命周期

**数据采集：**

```bash
# 按大小降序检查每个池
python .claude/script/tracy/tracy_http.py pool_allocations <pool> <start_ns> <end_ns> 0 50 size_descend
python .claude/script/tracy/tracy_http.py pool_allocations <pool> <start_ns> <end_ns> 0 50 appeared_at_ascend
```

重点检查：`thread_alloc_id` 对应的线程名是否与该池用途匹配。

**结论格式：**
```
⚠️ 【池错误】gpu 池发现 MainThread 分配：
  3 次，合计 48 MB，appeared_at = t+0.1s / t+2.3s / t+8.7s
  GPU 资源（纹理/Buffer）应在 RenderThread 内通过 RHI 接口创建
  → 推测：初始化时在主线程直接调用 GPU API，违反线程所有权规则
  风险：可能引发 GPU 驱动级竞态条件
```

---

### 【异常类型 3】内存分配导致帧卡顿

**判断标准：** 将存活分配的 `appeared_at` 时间与最差帧列表对比，检查最差帧时间窗口内是否有大额分配。

**数据采集：**

从 B 路径（或重新采样）拿到最差 5 帧的时间窗口，对每帧时间范围查询分配：

```bash
# 对最差帧时间范围精确查询
python .claude/script/tracy/tracy_http.py pool_allocations default <frame_start_ns> <frame_end_ns> 0 20 size_descend
```

同时查消息日志确认是否有 GC 触发信号：

```bash
python .claude/script/tracy/tracy_http.py messages 0 20 <frame_start_ns> <frame_end_ns>
```

**关联分析——分配与帧耗时的时序叠加：**

```
帧卡顿 × 内存分配 关联分析：

  帧 #847（83.2ms）：
    区间内分配：512 MB（default 池，thread=LoadThread）appeared_at=t+14.1s
    消息：SceneStreamIn: 24 assets loaded
    → 大额分配触发 allocator 锁竞争 + 内存页错误，阻塞主线程

  帧 #203（61.4ms）：
    区间内分配：18 次 × ~2MB（temp 池）
    → 高频分配导致 temp 池扩容，触发系统级 mmap 调用

  帧 #901（58.7ms）：
    区间内无大额分配，消息含 "GC: collect gen2"
    → GC 本身造成停顿（与分配无直接关系，属于运行时问题）
```

**结论格式：**
```
⚠️ 【分配卡顿】3 个最差帧（#847, #203, #901）确认与内存分配相关：
  #847：512MB 单次大分配，allocator 竞争导致主线程阻塞 ~40ms
  #203：18 次 temp 池扩容，系统 mmap 耗时 ~15ms
  #901：GC gen2 回收（与分配策略相关但非直接原因）
```

---

### 【异常类型 4】场景不该出现的内存分配

**判断标准：** 结合用户描述的场景（如"战斗中"、"主菜单"、"纯渲染帧"），识别与当前场景语义不符的分配。

**先向用户确认场景语义（一句话）：**
> 「你描述的是「战斗场景运行中的卡顿」——在战斗运行时，我预期不应有大型资产加载或场景初始化类的分配。接下来我会检查是否有此类分配出现。」

**数据采集——按时间顺序扫描大额或可疑分配：**

```bash
# 按出现时间排序，检查分配的"身份"
python .claude/script/tracy/tracy_http.py pool_allocations default <start_ns> <end_ns> 0 50 appeared_at_ascend
python .claude/script/tracy/tracy_http.py pool_allocations default <start_ns> <end_ns> 0 50 size_descend
```

**识别模式（结合 thread 名、alloc 大小、时间节奏）：**

| 分配特征 | 场景判断 | 异常信号 |
|----------|----------|---------|
| 战斗中出现 > 50MB 单次分配 | 疑似关卡/资产加载残留 | 应在进入战斗前完成 |
| 主菜单时 RenderThread 高频小分配 | 疑似 UI 动画每帧重建 | 应复用 UI 对象 |
| 纯渲染帧中 LoadThread 活跃 | 背景加载与渲染帧重叠 | 加载线程优先级问题 |
| 任意场景出现未释放的 ShaderCompile 相关分配 | Shader 编译未缓存 | 应在启动时预编译 |

结合 `is_freed` 字段：`is_freed = false` 且 `appeared_at` 在分析时间段内 → 确认为该场景期间产生的存活对象。

**结论格式：**
```
⚠️ 【场景异常】战斗运行阶段（t=5.2~18.6s）发现不符合预期的分配：

  异常 #1：t+8.4s，512MB，thread=LoadThread，is_freed=false
    → 场景资产在战斗运行中途加载，应提前到关卡进入时完成
    风险：持续占用物理内存，可能触发后续帧的内存压力

  异常 #2：t+10.1~14.8s，共 847 次 × 平均 4KB，thread=RenderThread
    → 每帧 ~100 次小分配，疑似 DrawCall 参数临时构建未复用
    场景预期：战斗运行帧应使用预分配的 DrawCall buffer，零临时分配

  异常 #3：t+12.3s，64MB，thread=MainThread，is_freed=false
    → 分配时机与消息 "ShaderCompile: 12 variants" 重合
    → Shader 变体在战斗中实时编译，应在关卡加载时预编译并缓存
```

---

## C4. 综合结论与优化建议

汇总所有命中的异常类型，按严重程度排序：

```
=== 内存分析结论 ===

命中异常（按严重程度）：

【P0】分配卡顿：3 个最差帧由内存分配直接导致（最差 83ms，损失 ~40ms）
【P1】场景异常：战斗阶段存在资产异步加载 + Shader 实时编译，累计 576MB 异常存活
【P2】池错误：gpu 池有 3 次 MainThread 分配（48MB），存在线程竞态风险
【P3】频繁分配：temp 池 79 次/帧，RenderThread 占主导，每帧产生不必要的 GC 压力

优化优先级：

【P0 — 设计层】将 SceneStreamIn 改为预加载（进关卡时同步完成），消除帧内大额分配
【P1 — 设计层】Shader 变体预编译到启动阶段，禁止运行时按需编译
【P2 — 架构层】GPU 资源创建移入 RenderThread，通过 Command 队列与 MainThread 通信
【P3 — 代码层】RenderThread 的 temp 分配改为帧级对象池（FrameArena），每帧 Reset 复用
```

代码层优化（P3）若源文件可访问，询问用户后调用 `booming-analysis-code-optimization` skill。
