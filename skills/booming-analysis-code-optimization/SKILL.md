---
name: booming-analysis-code-optimization
description: 由 booming-analysis-tracy-profile 调用——在已有 Tracy 热点 zone 数据且源文件本地可访问时使用。分析性能热点函数的代码上下文，给出具体优化步骤。不要直接触发，由 tracy-selection skill 传入 zone 数据后调用。
---

# 代码性能优化分析

基于 Tracy 热点数据，读取本地源文件，分析代码上下文，给出具体可执行的优化建议。

**保存分析结果到：** `docs/booming/{YYYY-MM-DD}-<feature-name>/opti-{YYYY-MM-DD-HH}-<feature-name>.md`

## 输入上下文

调用本 skill 时，调用方需提供：
- `zone`：热点 zone 的完整 JSON（含 function、file、line、duration_ns、children 耗时分布）
- `question`：用户的原始问题描述

## 分析流程

### 步骤 1：读取热点函数代码

读取 zone 的 `file` 字段对应的源文件，聚焦于 `line` 附近 ±50 行：

```python
# 读取热点行上下文
with open(zone["file"], encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
start = max(0, zone["line"] - 50)
end = min(len(lines), zone["line"] + 50)
context = "".join(lines[start:end])
```

### 步骤 2：探索相关上下文

根据代码内容，按需读取：
- 同目录的头文件（`.h` / `.hpp`）中的类/函数声明
- 被调用的子函数定义（如果在同一文件内）
- 相关数据结构定义

**限制**：最多额外读取 3 个文件，避免上下文过载。

### 步骤 3：结合 Tracy 数据分析

将 Tracy 耗时数据与代码逐一对应：

| 分析维度 | 关注点 |
|----------|--------|
| 热路径 | 耗时最长的调用链对应哪段代码 |
| 非 zone 耗时 | 父耗时 - 子耗时之和的部分对应哪些操作（内联函数、系统调用、锁等待）|
| 数据访问 | 是否有频繁的内存分配、容器遍历、字符串操作 |
| 同步开销 | 是否有锁、条件变量、原子操作 |
| 冗余计算 | 循环内是否有可提前计算的内容 |

### 步骤 4：给出优化建议

按优先级（影响 × 可行性）排列，每条建议包含：

1. **问题描述**：定位到具体行号，说明为什么慢
2. **优化方案**：给出修改后的伪代码或代码片段
3. **预期收益**：估算可减少多少耗时（基于 Tracy 数据推断）
4. **风险提示**：如有行为变化风险则注明

**输出格式示例：**

```
## 优化建议

### 1. 减少 tickCoherentInLogic 内的重复查询（预期节省 ~60%）

**问题**（chaos_ui_manager.cpp:925）：
每帧调用 GetWidget() 触发哈希表查找，Tracy 显示该段耗时 392ms，占总耗时 80%。

**优化**：
- 将 widget 指针缓存为成员变量，仅在 UI 结构变化时更新
- 修改前：`auto* w = GetWidget(id);`（每帧查找）
- 修改后：`// m_cachedWidget 在 OnUIChanged() 中更新`

**风险**：需确保 widget 生命周期与缓存一致，避免悬空指针。
```

### 步骤 5：汇总

分析完成后输出：
- 总结 1-2 句核心瓶颈原因
- 列出建议（按优先级排序）
- 如需进一步分析（更深调用栈、帧统计），提示配合 Tracy MCP 工具
