# 路径 A：选中 Zone 深度分析

适用场景：用户在 Tracy UI 中选中了某个 zone，或问"这个函数为什么慢"。

---

## A1. 读取选中 zone

```bash
python .claude/script/tracy/tracy_http.py selection
```

`valid: false` → 提示：「请在 Tracy UI 中点击选择一个 zone，选好后告诉我，我立即开始分析。」

---

## A2. 展示基础信息（必须含数字）

```
函数：RenderSystem::DrawBatch（src/render/batch.cpp:247）
线程：RenderThread（id: 12345）
耗时：18.3 ms（帧预算 16.7ms 的 109%）⚠️ 超预算
子 zone：7 个
```

---

## A3. 热点分解（并行查询所有子 zone）

对每个 `children_ids` 调用：

```bash
python .claude/script/tracy/tracy_http.py zone <zone_id>
```

构建耗时表，**自动过滤 < 1% 的子 zone**：

```
耗时分布（父 zone 18.3ms = 100%）：
  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  DrawMeshes       12.1ms  66%  ← 主要瓶颈
  ▓▓▓▓▓              UpdateUniforms    3.4ms  19%
  ▓▓                 SortDrawCalls     1.8ms  10%
  ░                  [非 zone 代码]    1.0ms   5%  (内联/系统调用)
  [已过滤 4 个 < 1% 子 zone]
```

**立即给出判断**：`DrawMeshes` 占 66%，是当前首要瓶颈，建议优先分析它。

---

## A4. 递归钻取热点

对占比 > 20% 且有子 zone 的节点，继续展开一层，递归最多 3 层或直到叶子节点：

```bash
python .claude/script/tracy/tracy_http.py zone_children <hot_zone_id>
```

每层展示同样格式的耗时表，并标注「深入第 N 层」。

---

## A5. 源码定位

```bash
python -c "import os; print(os.path.exists(r'{file}'))"
python .claude/script/tracy/find_file.py "{file}"
```

文件找到后展示精确位置：`src/render/batch.cpp:247 → DrawMeshes()`

询问：「是否对 `DrawMeshes` 进行代码级优化分析？」

用户确认后调用 `booming-analysis-code-optimization` skill，传入热点 zone 完整 JSON + 用户原始问题。

**文件查找顺序：**
1. 原路径直接检查
2. 工程目录模糊搜索：`python {skill_dir}/../script/tracy/find_file.py "{file}"`
3. 请用户提供根目录后重试
4. 仍未找到 → 跳过代码级分析，说明原因
