#!/usr/bin/env python3
"""
帧率统计分析脚本
用途：抓取全量帧数据，计算帧率分布、最差帧、百分位数等关键指标。

用法：
    python .claude/script/tracy/analyze_frames.py
    python .claude/script/tracy/analyze_frames.py --budget 16.67
    python .claude/script/tracy/analyze_frames.py --top 10

输出：帧率概况 + 最差N帧列表 + 百分位分布
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

SCRIPT_DIR = __file__.replace("analyze_frames.py", "")
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


def fetch_all_frames():
    """分页获取全量帧数据（每次最多1000帧）"""
    all_frames = []
    offset = 0
    batch = 1000
    while True:
        data = run_cmd(["frames", str(offset), str(batch)])
        total = data["total_count"]
        frames = data["frames"]
        all_frames.extend(frames)
        offset += len(frames)
        if offset >= total or not frames:
            break
    return all_frames, total


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0
    idx = int(len(sorted_vals) * p / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


def main():
    parser = argparse.ArgumentParser(description="Tracy 帧率统计分析")
    parser.add_argument("--budget", type=float, default=16.67, help="帧时间预算(ms), 默认 16.67ms (60FPS)")
    parser.add_argument("--top", type=int, default=5, help="显示最差N帧, 默认5")
    parser.add_argument("--json", action="store_true", help="输出原始JSON")
    args = parser.parse_args()

    budget_ns = args.budget * 1_000_000

    print("正在获取帧数据...", file=sys.stderr)
    frames, total_count = fetch_all_frames()

    if not frames:
        print(json.dumps({"error": "No frames found"}))
        sys.exit(1)

    durations_ns = [f["duration_ns"] for f in frames]
    durations_ms = [d / 1_000_000 for d in durations_ns]

    total_time_ms = sum(durations_ms)
    avg_ms = total_time_ms / len(durations_ms)
    min_ms = min(durations_ms)
    max_ms = max(durations_ms)

    sorted_dur = sorted(durations_ns)
    p50 = percentile(sorted_dur, 50) / 1_000_000
    p75 = percentile(sorted_dur, 75) / 1_000_000
    p90 = percentile(sorted_dur, 90) / 1_000_000
    p99 = percentile(sorted_dur, 99) / 1_000_000

    # 超预算帧
    budget_2x = budget_ns * 2
    over_budget = [(f["frame_idx"], f["duration_ns"] / 1_000_000) for f in frames if f["duration_ns"] > budget_ns]
    over_2x = [(idx, ms) for idx, ms in over_budget if ms * 1_000_000 > budget_2x]

    # 最差N帧
    sorted_frames = sorted(frames, key=lambda f: f["duration_ns"], reverse=True)
    top_frames = sorted_frames[:args.top]

    avg_fps = 1000.0 / avg_ms if avg_ms > 0 else 0

    if args.json:
        result = {
            "total_frames": total_count,
            "total_time_ms": round(total_time_ms, 1),
            "avg_ms": round(avg_ms, 2),
            "avg_fps": round(avg_fps, 1),
            "min_ms": round(min_ms, 2),
            "max_ms": round(max_ms, 2),
            "percentiles": {"p50": round(p50,2), "p75": round(p75,2), "p90": round(p90,2), "p99": round(p99,2)},
            "over_budget_count": len(over_budget),
            "over_budget_pct": round(len(over_budget) / len(frames) * 100, 1),
            "over_2x_count": len(over_2x),
            "top_frames": [
                {"frame_idx": f["frame_idx"], "duration_ms": round(f["duration_ns"]/1_000_000, 1),
                 "multiplier": round(f["duration_ns"] / budget_ns, 1)}
                for f in top_frames
            ]
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"\n=== 帧率统计（共 {total_count} 帧，总时长 {total_time_ms/1000:.1f}s）===")
    print(f"平均帧时：{avg_ms:.1f}ms（{avg_fps:.1f} FPS）")
    print(f"最差帧：第 {sorted_frames[0]['frame_idx']} 帧，{max_ms:.1f}ms（超预算 {max_ms/args.budget:.1f}×）")
    print(f"最优帧：{min_ms:.1f}ms")
    print()
    print(f"超预算帧（> {args.budget:.1f}ms = {1000/args.budget:.0f}FPS）：{len(over_budget)} 帧（{len(over_budget)/len(frames)*100:.1f}%）" + ("  ⚠️" if len(over_budget)/len(frames) > 0.05 else ""))
    print(f"超 2× 预算帧（> {args.budget*2:.1f}ms）：{len(over_2x)} 帧")
    print()
    print("百分位：")
    print(f"  P50={p50:.1f}ms  P75={p75:.1f}ms  P90={p90:.1f}ms  P99={p99:.1f}ms")
    print()
    print(f"最差 {args.top} 帧：")
    for f in top_frames:
        ms = f["duration_ns"] / 1_000_000
        mult = ms / args.budget
        tag = "  ⚠️" if mult > 2 else ""
        print(f"  #{f['frame_idx']:<6}  {ms:6.1f}ms  [+{mult:.1f}×]{tag}")


if __name__ == "__main__":
    main()
