#!/usr/bin/env python3
"""
Trace 概况快速摘要脚本
用途：一键输出 trace 基本信息、帧率、线程列表、内存池列表、Plot 列表。
      适合作为任何分析的起点，快速建立全局认知。

用法：
    python .claude/script/tracy/analyze_overview.py
    python .claude/script/tracy/analyze_overview.py --json

输出：程序信息 + 帧率摘要 + 各类资源计数
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

SCRIPT_DIR = __file__.replace("analyze_overview.py", "")
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


def main():
    parser = argparse.ArgumentParser(description="Tracy Trace 概况分析")
    parser.add_argument("--json", action="store_true", help="输出原始JSON")
    args = parser.parse_args()

    # 并发获取（串行执行，避免端口竞争）
    print("正在获取 trace 概况...", file=sys.stderr)
    info = run_cmd(["trace_info"])
    overview = run_cmd(["trace_overview"])
    threads = run_cmd(["threads"], allow_fail=True)
    plots = run_cmd(["plots"], allow_fail=True)
    pools = run_cmd(["pools"], allow_fail=True)

    if args.json:
        print(json.dumps({
            "trace_info": info,
            "trace_overview": overview,
            "threads": threads,
            "plots": plots,
            "pools": pools,
        }, ensure_ascii=False, indent=2))
        return

    # === 基础信息 ===
    prog = overview.get("captured_program", "?")
    host = overview.get("host_info", info.get("host", "?"))
    first_ns = overview.get("first_time", 0)
    last_ns = overview.get("last_time", 0)
    duration_ms = (last_ns - first_ns) / 1_000_000
    frame_count = overview.get("frame_count", 0)
    zone_count = overview.get("zone_count", 0)
    msg_count = overview.get("message_count", 0)
    lock_count = overview.get("lock_count", 0)
    plot_count = overview.get("plot_count", 0)

    print(f"\n=== Trace 基础信息 ===")
    print(f"程序：{prog}")
    print(f"主机：{host}")

    timing = info.get("timing", {})
    if timing:
        pid = timing.get("pid", "?")
        res_ns = timing.get("resolution_ns", 0)
        print(f"PID：{pid}   时钟精度：{res_ns} ns")

    app_info = info.get("app_info", [])
    if app_info:
        print(f"App Info：{' / '.join(app_info)}")

    cpu_topo = info.get("cpu_topology", {})
    if cpu_topo:
        pkg_count = len(cpu_topo)
        total_threads = sum(
            len(thread_list)
            for pkg in cpu_topo.values()
            for die in pkg.values()
            for thread_list in die.values()
        )
        print(f"CPU：{pkg_count} 个 Package，共 {total_threads} 个逻辑核")

    print()
    print(f"=== Trace 时长与规模 ===")
    print(f"时长：{duration_ms/1000:.2f}s   帧数：{frame_count}")
    print(f"Zone 总数：{zone_count:,}   消息：{msg_count:,}   锁：{lock_count:,}   Plot：{plot_count}")

    # 帧统计（来自 trace_info）
    fs = info.get("frame_stats", {})
    if fs:
        avg_ms = fs.get("avg_frame_ns", 0) / 1_000_000
        min_ms = fs.get("min_frame_ns", 0) / 1_000_000
        max_ms = fs.get("max_frame_ns", 0) / 1_000_000
        avg_fps = 1000 / avg_ms if avg_ms > 0 else 0
        print()
        print(f"=== 帧率概况（来自 trace_info）===")
        print(f"平均帧时：{avg_ms:.1f}ms（{avg_fps:.1f} FPS）")
        print(f"最差帧：{max_ms:.1f}ms   最优帧：{min_ms:.1f}ms")

    # 线程列表
    thread_list = threads.get("threads", [])
    if thread_list:
        print()
        print(f"=== 线程列表（共 {len(thread_list)} 个）===")
        for t in thread_list[:20]:  # 最多显示20个
            print(f"  [{t.get('thread_id')}] {t.get('thread_name', '?')}")
        if len(thread_list) > 20:
            print(f"  ... 共 {len(thread_list)} 个线程")

    # Plot 列表
    plot_names = plots.get("plots", [])
    if plot_names:
        print()
        print(f"=== Plot 列表（{len(plot_names)} 个）===")
        for p in plot_names:
            print(f"  {p}")

    # 内存池列表
    pool_names = pools.get("pools", [])
    if pool_names:
        print()
        print(f"=== 内存池列表（{len(pool_names)} 个）===")
        for p in pool_names:
            print(f"  {p}")


if __name__ == "__main__":
    main()
