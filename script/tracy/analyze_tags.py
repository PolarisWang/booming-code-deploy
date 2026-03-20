#!/usr/bin/env python3
"""
CPU Tag 耗时聚合分析脚本
用途：从 stats_frame_tags 数据中计算各 Tag 的全程累计耗时、平均每帧耗时、
      并行度、空闲率，按层级树形展示。

用法：
    python .claude/script/tracy/analyze_tags.py
    python .claude/script/tracy/analyze_tags.py --json
    python .claude/script/tracy/analyze_tags.py --filter logic

输出：Tag 层级耗时树 + 异常标注
"""

import json
import sys
import subprocess
import argparse
import io

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = __file__.replace("analyze_tags.py", "")
TRACY_HTTP = SCRIPT_DIR + "tracy_http.py"


def run_cmd(cmd_args):
    result = subprocess.run(
        [sys.executable, TRACY_HTTP] + cmd_args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stdout.strip(), file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def mean(vals):
    valid = [v for v in vals if v >= 0]
    return sum(valid) / len(valid) if valid else 0.0


def compute_tag_summary(tag_data):
    """计算单个 tag 的聚合统计"""
    self_times = tag_data.get("self_times", [])
    all_times = tag_data.get("all_times", [])
    span_times = tag_data.get("span_times", [])
    idle_ratios = tag_data.get("idle_ratios", [])
    parallel_ratios = tag_data.get("parallel_ratios", [])

    n = len(span_times)
    # 过滤无效帧（span_time=0）
    valid_span = [s for s in span_times if s > 0]

    total_span_ms = sum(valid_span) / 1_000_000
    total_all_ms = sum(all_times) / 1_000_000
    total_self_ms = sum(self_times) / 1_000_000
    avg_span_ms = total_span_ms / n if n > 0 else 0
    avg_all_ms = total_all_ms / n if n > 0 else 0

    avg_idle_ratio = mean(idle_ratios)
    avg_parallel = mean(parallel_ratios)

    return {
        "total_span_ms": total_span_ms,
        "total_all_ms": total_all_ms,
        "total_self_ms": total_self_ms,
        "avg_span_ms": avg_span_ms,
        "avg_all_ms": avg_all_ms,
        "avg_idle_ratio": avg_idle_ratio,
        "avg_parallel": avg_parallel,
        "frame_count": n,
    }


def build_tree(tags_summary):
    """
    按 tag 名称前缀构建层级树。
    约定：tag 名称用 _ 分隔，父节点是前缀。
    根节点 = 不含 _ 的 tag（或 'all'/'undefined'）。
    """
    names = sorted(tags_summary.keys())
    children = {n: [] for n in names}

    for name in names:
        parts = name.split("_")
        if len(parts) <= 1:
            continue
        # 找最近的父节点（从最长前缀向上查找）
        for depth in range(len(parts) - 1, 0, -1):
            parent = "_".join(parts[:depth])
            if parent in tags_summary:
                children[parent].append(name)
                break

    # 根节点：没有被任何其他节点收录为子节点的
    all_children = set(c for cs in children.values() for c in cs)
    roots = [n for n in names if n not in all_children]
    return roots, children


def print_tree(name, children, tags_summary, indent, total_span_ms, filter_prefix):
    if filter_prefix and not name.startswith(filter_prefix):
        # 仍然递归子节点
        for child in sorted(children.get(name, []), key=lambda x: -tags_summary[x]["total_span_ms"]):
            print_tree(child, children, tags_summary, indent, total_span_ms, filter_prefix)
        return

    s = tags_summary[name]
    pct = s["total_span_ms"] / total_span_ms * 100 if total_span_ms > 0 else 0
    prefix = "  " * indent + ("▼ " if children.get(name) else "  ")

    idle_str = ""
    if s["avg_idle_ratio"] >= 0:
        idle_str = f"   idle: {s['avg_idle_ratio']*100:.0f}%"
        if s["avg_idle_ratio"] > 0.20:
            idle_str += " ⚠️多线程利用率低"

    bottleneck = ""
    if pct > 50:
        bottleneck = "   ← 主要瓶颈"

    print(f"{prefix}{name:<45}  {s['total_span_ms']:>8.1f}ms  {pct:>5.1f}%   avg/frame: {s['avg_span_ms']:>5.2f}ms{idle_str}{bottleneck}")

    for child in sorted(children.get(name, []), key=lambda x: -tags_summary[x]["total_span_ms"]):
        print_tree(child, children, tags_summary, indent + 1, total_span_ms, filter_prefix)


def main():
    parser = argparse.ArgumentParser(description="Tracy CPU Tag 耗时分析")
    parser.add_argument("--json", action="store_true", help="输出原始JSON")
    parser.add_argument("--filter", type=str, default="", help="只显示指定前缀的 tag（如 logic）")
    args = parser.parse_args()

    print("正在获取 Tag 统计...", file=sys.stderr)
    data = run_cmd(["stats_frame_tags"])

    if "error" in data:
        print(json.dumps({"error": data["error"]}))
        sys.exit(1)

    # data 是列表
    tag_list = data if isinstance(data, list) else data.get("tags", [])

    tags_summary = {}
    for tag in tag_list:
        name = tag.get("tag_name", "")
        if not name:
            continue
        tags_summary[name] = compute_tag_summary(tag)

    if args.json:
        print(json.dumps(tags_summary, ensure_ascii=False, indent=2))
        return

    if not tags_summary:
        print("无 Tag 数据")
        return

    roots, children = build_tree(tags_summary)

    # 总基准：所有根节点 span_time 之和（排除 all/undefined）
    root_tags = [r for r in roots if r not in ("all", "undefined")]
    total_span_ms = sum(tags_summary[r]["total_span_ms"] for r in root_tags)
    if total_span_ms == 0:
        total_span_ms = sum(s["total_span_ms"] for s in tags_summary.values())

    n_frames = max((s["frame_count"] for s in tags_summary.values()), default=0)
    print(f"\n=== CPU Tag 耗时分析（全程 {total_span_ms/1000:.1f}s，{n_frames} 帧）===")
    print(f"{'Tag':<47}  {'总span':>10}  {'占比':>6}   {'avg/帧':>10}   空闲率")
    print("-" * 90)

    # 优先输出已知根节点顺序（all/undefined 放最后）
    ordered_roots = [r for r in roots if r not in ("all", "undefined")]
    ordered_roots += [r for r in roots if r in ("all", "undefined")]

    filter_prefix = args.filter or ""
    for root in ordered_roots:
        print_tree(root, children, tags_summary, 0, total_span_ms, filter_prefix)
        if not filter_prefix or root.startswith(filter_prefix):
            print()


if __name__ == "__main__":
    main()
