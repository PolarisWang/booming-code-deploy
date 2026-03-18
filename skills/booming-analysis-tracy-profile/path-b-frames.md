# 路径 B：帧级性能分析

适用场景："哪帧最慢"、"卡顿"、"掉帧"、frame 相关问题。

---

## B1. 采样帧数据

```bash
python .claude/script/tracy/tracy_http.py frames 0 1000
```

---

## B2. 计算关键指标，主动给结论

**立即输出**（不要先展示原始数据）：

```
帧率概况（共 1,247 帧，总时长 20.8s）：
  平均帧时：16.7ms（59.9 FPS）
  最差帧：第 847 帧，83.2ms（掉帧 4.9×）
  超 33ms（30FPS 以下）：23 帧（1.8%）
  超 16.7ms（60FPS 以下）：187 帧（15.0%）⚠️ 明显波动

最差 5 帧：
  #847   83.2ms   [+5.0×]
  #203   61.4ms   [+3.7×]
  #901   58.7ms   [+3.5×]
  #156   47.3ms   [+2.8×]
  #512   42.1ms   [+2.5×]
```

---

## B3. 定位最差帧时间范围，查询上下文

取最差帧（及次差 2-3 帧）的 `start_ns` / `end_ns`，并行查询：

```bash
# 查最差帧区间内的消息日志
python .claude/script/tracy/tracy_http.py messages 0 50 <start_ns> <end_ns>

# 查 Plot 数据（如有 FPS/CPU/GPU 等曲线，取同一时间窗口）
python .claude/script/tracy/tracy_http.py plots
python .claude/script/tracy/tracy_http.py plot_values <plot_name> 0 200 <start_ns> <end_ns>
```

消息日志若含 GC、加载、I/O、Stall、Flush 等关键词，直接标注为触发信号。

---

## B4. Zone 级精细分析（最差帧的 2-3 层钻取）

**仅对最差帧执行**，目标是从帧级定位到具体函数：

```bash
# 读取当前选中 zone（引导用户在 Tracy UI 中选中最差帧的根 zone）
python .claude/script/tracy/tracy_http.py selection
```

若用户已在 UI 中选中了目标帧的 zone，直接使用；否则提示：
> 「请在 Tracy UI 中点击第 847 帧（t=14.1s 附近）的根 zone，我来深入分析它的耗时分布。」

获得 zone 后，展开子 zone 耗时（与路径 A 相同的热点分解逻辑）：

```bash
python .claude/script/tracy/tracy_http.py zone_children <zone_id>
```

**构建该帧的完整耗时瀑布（最多 3 层，过滤 < 2% 节点）：**

```
第 847 帧耗时分解（83.2ms = 100%）：

Layer 1 — 根 zone：
  ▓▓▓▓▓▓▓▓▓▓▓▓▓  GameLoop::Update     68.4ms  82%  ← 主要来源
  ▓▓▓              GameLoop::Render     11.3ms  14%
  ░                GameLoop::Present     3.5ms   4%

Layer 2 — GameLoop::Update 展开（68.4ms）：
  ▓▓▓▓▓▓▓▓▓▓▓▓▓  SceneManager::Load   54.7ms  80%  ⚠️ 异常
  ▓▓▓              PhysicsWorld::Step    8.9ms  13%
  ▓                AISystem::Tick        4.8ms   7%

Layer 3 — SceneManager::Load 展开（54.7ms）：
  ▓▓▓▓▓▓▓▓▓▓▓▓▓  FileIO::ReadSync     48.1ms  88%  ← 同步 I/O 根因
  ▓                ResourceCache::Parse  6.6ms  12%
```

**同帧对比（与相邻正常帧比较）**：

取相邻正常帧（如第 846 帧）的同名 zone 耗时，量化异常幅度：

```
SceneManager::Load 耗时对比：
  正常帧（#846）：0.3ms
  最差帧（#847）：54.7ms  → 异常 182×
```

---

## B5. 精细结论与分层优化建议

**结论必须含以下要素：**
1. 根因函数（精确到文件:行号）
2. 触发条件（什么事件导致该帧异常）
3. 影响量化（与正常帧的对比倍数）

**输出格式：**

```
=== 最差帧（#847）分析结论 ===

根因：FileIO::ReadSync（src/scene/scene_manager.cpp:183）
  - 执行了同步文件读取，阻塞主线程 48.1ms
  - 触发条件：SceneManager::Load 在帧内被调用（消息日志：SceneStreamIn: 24 assets loaded）
  - 异常幅度：正常帧该路径耗时 ~0ms（不调用），此帧 48.1ms

影响范围：
  - 仅第 847 帧命中（属于单次尖刺，非持续性问题）
  - 次差帧（#203, 61.4ms）消息含 "SceneStreamIn: 18 assets"，同类问题

=== 优化建议（按优先级）===

【P0 — 设计层】异步化场景流式加载
  问题：SceneManager::Load 在游戏主循环内同步执行文件 I/O
  建议：将资产加载移入独立 I/O 线程（AssetLoader），主线程只做状态轮询
  预期收益：消除所有 SceneStreamIn 相关的帧尖刺（当前 23 帧中约 60% 由此引起）
  参考：FileIO::ReadSync → AsyncIO::ReadAsync + 回调/future

【P1 — 代码层】ResourceCache::Parse 可优化
  问题：ResourceCache::Parse 在加载完成后串行执行（6.6ms），可与其他系统并行
  建议：将 Parse 阶段改为 WorkerPool 任务，主线程等待完成信号
  预期收益：减少约 6ms 主线程阻塞

【P2 — 调度层】PhysicsWorld::Step 在异常帧不应全量执行
  问题：即便主线程已超预算，PhysicsWorld::Step 仍执行完整 8.9ms
  建议：引入帧时间预算检查，超预算时跳过非关键物理（如静态场景）
  预期收益：可为最差帧节省 4-6ms
```

**代码级优化分析**（针对代码层建议）：

若根因函数源文件在本地可访问，询问：
> 「是否对 `FileIO::ReadSync`（src/scene/scene_manager.cpp:183）进行代码级优化分析？」

用户确认后调用 `booming-analysis-code-optimization` skill，传入：
- 热点 zone 完整 JSON（函数名、本地实际文件路径、行号、耗时、子 zone 分布）
- 用户原始问题描述
- 本次分析的优化方向摘要（作为上下文）

**文件查找顺序：**
1. 原路径直接检查：`python -c "import os; print(os.path.exists(r'{file}'))"`
2. 工程目录模糊搜索：`python {skill_dir}/../script/tracy/find_file.py "{file}"`
3. 请用户提供根目录后重试
4. 仍未找到 → 跳过代码级分析，说明原因，仅保留设计层和调度层建议
