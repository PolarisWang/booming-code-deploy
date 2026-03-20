#!/usr/bin/env python3
"""
内存池分析脚本
用途：对所有内存池执行全程 overview，统计分配次数、总分配量、存活量（疑似泄漏），
      标注异常池。支持对单个池进行深度泄漏分布分析。

用法：
    python .claude/script/tracy/analyze_memory.py
    python .claude/script/tracy/analyze_memory.py --pool PoolDefault
    python .claude/script/tracy/analyze_memory.py --pool PoolDefault --leak-detail
    python .claude/script/tracy/analyze_memory.py --json

输出：各内存池摘要表 + 异常标注，--leak-detail 输出单池泄漏的线程/时间分布
"""

import json
import sys
import subprocess
import argparse
import io
from collections import defaultdict

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = __file__.replace("analyze_memory.py", "")
TRACY_HTTP = SCRIPT_DIR + "tracy_http.py"


def run_cmd(cmd_args, allow_fail=False):
    result = subprocess.run(
        [sys.executable, TRACY_HTTP] + cmd_args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        if allow_fail:
            return {}
        print(result.stdout.strip(), file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def fmt_bytes(n):
    if n >= 1024 ** 3:
        return f"{n/1024**3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n/1024**2:.1f} MB"
    if n >= 1024:
        return f"{n/1024:.1f} KB"
    return f"{n} B"


def get_thread_name_map(threads_data):
    """将线程列表转为 {thread_id: thread_name} 映射"""
    result = {}
    for t in threads_data.get("threads", []):
        tid = t.get("thread_id", 0)
        name = t.get("thread_name", "") or f"tid={tid}"
        result[tid] = name
    return result


def analyze_pool_leak_detail(pool, first_ns, last_ns, thread_map, sample_count=500, bucket_seconds=20):
    """
    深度分析单个内存池的泄漏分布：
    - 按线程统计泄漏块数/大小
    - 按时间桶统计泄漏分布（每 bucket_seconds 秒一桶）
    - 打印前 N 个最大泄漏块

    参数:
        pool            内存池名称
        first_ns        trace 起始时间戳（纳秒）
        last_ns         trace 结束时间戳（纳秒）
        thread_map      {thread_id: thread_name}
        sample_count    从 pool_allocations 拉取的样本数（按 size 降序）
        bucket_seconds  时间分桶宽度（秒）
    """
    data = run_cmd([
        "pool_allocations", pool,
        str(first_ns), str(last_ns),
        "0", str(sample_count), "size_descend"
    ], allow_fail=True)

    if not data or "error" in data:
        print(f"  无法获取 {pool} 的分配记录")
        return

    allocs = data.get("allocations", [])
    total_count = data.get("total_count", 0)
    leaked = [a for a in allocs if not a.get("is_freed", True)]

    if not leaked:
        print(f"  样本 {len(allocs)} 条（共 {total_count:,} 条）中无未释放分配")
        return

    print(f"\n  样本 {len(allocs)} 条（共 {total_count:,} 条），其中未释放 {len(leaked)} 条")

    # 按线程分组
    by_thread = defaultdict(lambda: {"count": 0, "bytes": 0, "items": []})
    for a in leaked:
        tid = a["thread_alloc_id"]
        by_thread[tid]["count"] += 1
        by_thread[tid]["bytes"] += a["size"]
        by_thread[tid]["items"].append(a)

    print("\n  === 泄漏按线程分组 ===")
    for tid, info in sorted(by_thread.items(), key=lambda x: -x[1]["bytes"]):
        name = thread_map.get(tid, f"tid={tid}")
        print(f"  [{name}]  {info['count']} 块  {fmt_bytes(info['bytes'])}")
        for a in sorted(info["items"], key=lambda x: -x["size"])[:3]:
            t = (a["appeared_at"] - first_ns) / 1e9
            print(f"    {fmt_bytes(a['size']):>10}  at t={t:.1f}s")

    # 按时间桶分布
    print(f"\n  === 泄漏时间分布（每 {bucket_seconds}s 一桶）===")
    buckets = defaultdict(lambda: {"count": 0, "bytes": 0})
    for a in leaked:
        bucket = int((a["appeared_at"] - first_ns) / 1e9 / bucket_seconds) * bucket_seconds
        buckets[bucket]["count"] += 1
        buckets[bucket]["bytes"] += a["size"]
    for t in sorted(buckets):
        b = buckets[t]
        bar = "#" * min(40, max(1, int(b["bytes"] / 1024 / 1024)))
        print(f"  t={t:4d}-{t+bucket_seconds:4d}s: {b['count']:3d} 块  {fmt_bytes(b['bytes']):>10}  {bar}")

    # 最大泄漏块 top10
    print("\n  === 最大泄漏块 Top10 ===")
    for a in sorted(leaked, key=lambda x: -x["size"])[:10]:
        t = (a["appeared_at"] - first_ns) / 1e9
        name = thread_map.get(a["thread_alloc_id"], f"tid={a['thread_alloc_id']}")
        print(f"  {fmt_bytes(a['size']):>10}  at t={t:.1f}s  thread=[{name}]")


def analyze_pool_freed_lifetime(pool, first_ns, last_ns, min_size_mb=50, sample_count=200):
    """
    分析单个池中已释放的大块分配的生命周期（alloc→free 时长）。
    用于判断大块内存的临时使用模式（是否是短暂 spike 还是长期持有）。

    参数:
        pool            内存池名称
        first_ns        trace 起始时间戳（纳秒）
        last_ns         trace 结束时间戳（纳秒）
        min_size_mb     只显示超过此大小（MB）的块
        sample_count    从 pool_allocations 拉取的样本数（按 size 降序）
    """
    data = run_cmd([
        "pool_allocations", pool,
        str(first_ns), str(last_ns),
        "0", str(sample_count), "size_descend"
    ], allow_fail=True)

    if not data or "error" in data:
        return

    allocs = data.get("allocations", [])
    min_size = min_size_mb * 1024 * 1024
    big_freed = [a for a in allocs if a.get("is_freed", False) and a["size"] >= min_size]

    if not big_freed:
        print(f"  样本中无 >{min_size_mb}MB 的已释放分配")
        return

    print(f"\n  === 已释放大块（>{min_size_mb}MB）生命周期 ===")
    for a in sorted(big_freed, key=lambda x: -x["size"])[:10]:
        t_alloc = (a["appeared_at"] - first_ns) / 1e9
        t_free = (a["free_time"] - first_ns) / 1e9
        lifetime = t_free - t_alloc
        print(f"  {fmt_bytes(a['size']):>10}  alloc=t+{t_alloc:.1f}s  free=t+{t_free:.1f}s  "
              f"lifetime={lifetime:.2f}s  tid={a['thread_alloc_id']}")


def main():
    parser = argparse.ArgumentParser(description="Tracy 内存池分析")
    parser.add_argument("--pool", type=str, default="", help="只分析指定内存池（默认全部）")
    parser.add_argument("--leak-detail", action="store_true",
                        help="对指定池（需配合 --pool）输出泄漏的线程/时间分布详情")
    parser.add_argument("--freed-lifetime", action="store_true",
                        help="对指定池（需配合 --pool）分析已释放大块的生命周期")
    parser.add_argument("--min-size-mb", type=int, default=50,
                        help="--freed-lifetime 时的最小块大小（MB），默认 50")
    parser.add_argument("--sample", type=int, default=500,
                        help="--leak-detail / --freed-lifetime 时的采样条数，默认 500")
    parser.add_argument("--bucket", type=int, default=20,
                        help="--leak-detail 时的时间分桶宽度（秒），默认 20")
    parser.add_argument("--json", action="store_true", help="输出原始JSON（仅 overview 模式）")
    args = parser.parse_args()

    # 获取时间范围
    overview = run_cmd(["trace_overview"])
    first_ns = overview.get("first_time", 0)
    last_ns = overview.get("last_time", 0)
    frame_count = max(overview.get("frame_count", 1), 1)

    if last_ns <= first_ns:
        print(json.dumps({"error": "Invalid trace time range"}))
        sys.exit(1)

    # 获取线程名映射（leak-detail 需要）
    thread_map = {}
    if args.leak_detail or args.freed_lifetime:
        threads_data = run_cmd(["threads"], allow_fail=True)
        thread_map = get_thread_name_map(threads_data)

    # 获取所有内存池
    pools_data = run_cmd(["pools"])
    pool_names = pools_data.get("pools", [])

    if not pool_names:
        print("此 trace 未记录内存分配数据")
        return

    if args.pool:
        pool_names = [p for p in pool_names if p == args.pool or args.pool in p]
        if not pool_names:
            print(f"未找到匹配的内存池：{args.pool}")
            sys.exit(1)

    print(f"正在分析 {len(pool_names)} 个内存池...", file=sys.stderr)

    results = []
    for pool in pool_names:
        data = run_cmd(["pool_overview", pool, str(first_ns), str(last_ns)], allow_fail=True)
        if not data or "error" in data:
            continue
        alloc_count = data.get("alloc_count", 0)
        free_count = data.get("free_count", 0)
        alloc_bytes = data.get("alloc_bytes", 0)
        free_bytes = data.get("free_bytes", 0)
        active_count = data.get("active_count", 0)
        active_bytes = data.get("active_bytes", 0)
        survive_rate = active_count / alloc_count if alloc_count > 0 else 0
        alloc_per_frame = alloc_count / frame_count

        results.append({
            "pool": pool,
            "alloc_count": alloc_count,
            "alloc_bytes": alloc_bytes,
            "free_count": free_count,
            "active_count": active_count,
            "active_bytes": active_bytes,
            "survive_rate": survive_rate,
            "alloc_per_frame": alloc_per_frame,
        })

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        print("无法获取内存池数据")
        return

    total_active_bytes = sum(r["active_bytes"] for r in results)

    print(f"\n=== 内存池摘要（trace 全程 {(last_ns-first_ns)/1e9:.1f}s，{frame_count} 帧）===")
    print(f"{'池名':<30}  {'总分配次':>10}  {'总分配量':>12}  {'存活次':>8}  {'存活量':>12}  {'存活率':>8}  备注")
    print("-" * 110)

    for r in sorted(results, key=lambda x: -x["active_bytes"]):
        notes = []
        if r["survive_rate"] > 0.01:
            notes.append("⚠️ 疑似泄漏")
        if r["alloc_per_frame"] > 50:
            notes.append(f"频繁分配 {r['alloc_per_frame']:.0f}次/帧")

        note_str = "  ".join(notes)
        print(f"{r['pool']:<30}  {r['alloc_count']:>10,}  {fmt_bytes(r['alloc_bytes']):>12}  "
              f"{r['active_count']:>8,}  {fmt_bytes(r['active_bytes']):>12}  {r['survive_rate']*100:>7.1f}%  {note_str}")

    print("-" * 110)
    print(f"总存活内存：{fmt_bytes(total_active_bytes)}")

    # 深度泄漏分布（需指定 --pool --leak-detail）
    if args.leak_detail:
        if not args.pool:
            print("\n[!] --leak-detail 需要配合 --pool 指定单个内存池", file=sys.stderr)
        else:
            print(f"\n{'='*60}")
            print(f"=== 泄漏深度分析：{pool_names[0]} ===")
            analyze_pool_leak_detail(
                pool_names[0], first_ns, last_ns, thread_map,
                sample_count=args.sample, bucket_seconds=args.bucket
            )

    # 已释放大块生命周期（需指定 --pool --freed-lifetime）
    if args.freed_lifetime:
        if not args.pool:
            print("\n[!] --freed-lifetime 需要配合 --pool 指定单个内存池", file=sys.stderr)
        else:
            print(f"\n{'='*60}")
            print(f"=== 已释放大块生命周期：{pool_names[0]} ===")
            analyze_pool_freed_lifetime(
                pool_names[0], first_ns, last_ns,
                min_size_mb=args.min_size_mb, sample_count=args.sample
            )


if __name__ == "__main__":
    main()
