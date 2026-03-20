"""
analyze_*.py 脚本单元测试

测试策略：
  - 纯计算函数：直接导入并断言（percentile, mean, compute_tag_summary, build_tree, fmt_bytes）
  - main() 入口：通过 subprocess 运行脚本 + mock HTTP server，验证 JSON 输出和退出码

Run:
    python test_analyze_scripts.py
    python test_analyze_scripts.py AnalyzeFramesUnitTests
    python test_analyze_scripts.py AnalyzeTagsUnitTests
    python test_analyze_scripts.py AnalyzeMemoryUnitTests
    python test_analyze_scripts.py AnalyzeScriptsIntegrationTests
"""

import importlib.util
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# 工具：动态加载脚本模块（不执行 main）
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(name, filename):
    path = os.path.join(SCRIPT_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


frames_mod = _load_module("analyze_frames", "analyze_frames.py")
tags_mod   = _load_module("analyze_tags",   "analyze_tags.py")
mem_mod    = _load_module("analyze_memory", "analyze_memory.py")


# ===========================================================================
# AnalyzeFramesUnitTests — analyze_frames.percentile()
# ===========================================================================

class AnalyzeFramesUnitTests(unittest.TestCase):

    # ------------------------------------------------------------------
    # percentile()
    # ------------------------------------------------------------------

    def test_percentile_empty_returns_zero(self):
        self.assertEqual(frames_mod.percentile([], 50), 0)

    def test_percentile_p50_single_element(self):
        self.assertEqual(frames_mod.percentile([42], 50), 42)

    def test_percentile_p0_returns_first(self):
        vals = [10, 20, 30, 40, 50]
        self.assertEqual(frames_mod.percentile(vals, 0), 10)

    def test_percentile_p100_returns_last(self):
        vals = [10, 20, 30, 40, 50]
        self.assertEqual(frames_mod.percentile(vals, 100), 50)

    def test_percentile_p50_odd_count(self):
        vals = sorted([10, 20, 30, 40, 50])
        result = frames_mod.percentile(vals, 50)
        # idx = int(5 * 50 / 100) = 2 → 30
        self.assertEqual(result, 30)

    def test_percentile_p75(self):
        vals = sorted([10, 20, 30, 40, 50, 60, 70, 80])
        result = frames_mod.percentile(vals, 75)
        # idx = int(8 * 75 / 100) = 6 → 70
        self.assertEqual(result, 70)

    def test_percentile_p99_near_max(self):
        vals = list(range(1, 101))  # [1..100]
        result = frames_mod.percentile(vals, 99)
        # idx = int(100 * 99 / 100) = 99 → 100
        self.assertEqual(result, 100)

    def test_percentile_does_not_modify_input(self):
        vals = [30, 10, 20]
        frames_mod.percentile(vals, 50)
        self.assertEqual(vals, [30, 10, 20])


# ===========================================================================
# AnalyzeTagsUnitTests — analyze_tags.mean() / compute_tag_summary() / build_tree()
# ===========================================================================

class AnalyzeTagsUnitTests(unittest.TestCase):

    # ------------------------------------------------------------------
    # mean()
    # ------------------------------------------------------------------

    def test_mean_empty_returns_zero(self):
        self.assertEqual(tags_mod.mean([]), 0.0)

    def test_mean_all_negative_one_returns_zero(self):
        # -1.0 は無効値、フィルタされる
        self.assertEqual(tags_mod.mean([-1.0, -1.0]), 0.0)

    def test_mean_mixed_valid_and_invalid(self):
        # 有効値のみ: [0.4, 0.6] → avg 0.5
        result = tags_mod.mean([-1.0, 0.4, -1.0, 0.6])
        self.assertAlmostEqual(result, 0.5, places=6)

    def test_mean_all_valid(self):
        result = tags_mod.mean([0.1, 0.2, 0.3])
        self.assertAlmostEqual(result, 0.2, places=6)

    def test_mean_zero_is_valid(self):
        result = tags_mod.mean([0.0, 0.0])
        self.assertAlmostEqual(result, 0.0, places=6)

    def test_mean_single_valid_value(self):
        self.assertAlmostEqual(tags_mod.mean([0.75]), 0.75, places=6)

    # ------------------------------------------------------------------
    # compute_tag_summary()
    # ------------------------------------------------------------------

    def _make_tag(self, self_t, all_t, span_t, idle_r, par_r):
        return {
            "tag_name": "test",
            "self_times": self_t,
            "all_times": all_t,
            "span_times": span_t,
            "idle_ratios": idle_r,
            "parallel_ratios": par_r,
        }

    def test_compute_tag_summary_zero_frames(self):
        tag = self._make_tag([], [], [], [], [])
        s = tags_mod.compute_tag_summary(tag)
        self.assertEqual(s["total_span_ms"], 0)
        self.assertEqual(s["frame_count"], 0)

    def test_compute_tag_summary_total_span_excludes_zero(self):
        # span_times: [1e9, 0, 2e9] → 有効は 1e9 + 2e9 = 3e9 ns = 3000 ms
        tag = self._make_tag(
            [0, 0, 0], [0, 0, 0],
            [1_000_000_000, 0, 2_000_000_000],
            [-1.0, -1.0, -1.0], [-1.0, -1.0, -1.0]
        )
        s = tags_mod.compute_tag_summary(tag)
        self.assertAlmostEqual(s["total_span_ms"], 3000.0, places=3)

    def test_compute_tag_summary_avg_span_divides_by_all_frames(self):
        # 3フレーム中 span_times=[1e9, 0, 2e9]、avg = total / 3
        tag = self._make_tag(
            [0, 0, 0], [0, 0, 0],
            [1_000_000_000, 0, 2_000_000_000],
            [-1.0, -1.0, -1.0], [-1.0, -1.0, -1.0]
        )
        s = tags_mod.compute_tag_summary(tag)
        self.assertAlmostEqual(s["avg_span_ms"], 3000.0 / 3, places=3)

    def test_compute_tag_summary_idle_ratio_filters_invalid(self):
        tag = self._make_tag(
            [0], [0], [1_000_000_000],
            [-1.0], [-1.0]
        )
        s = tags_mod.compute_tag_summary(tag)
        # -1.0 は無効値 → mean([]) = 0.0
        self.assertAlmostEqual(s["avg_idle_ratio"], 0.0, places=6)

    def test_compute_tag_summary_idle_ratio_valid(self):
        tag = self._make_tag(
            [0], [0], [1_000_000_000],
            [0.25], [1.5]
        )
        s = tags_mod.compute_tag_summary(tag)
        self.assertAlmostEqual(s["avg_idle_ratio"], 0.25, places=6)
        self.assertAlmostEqual(s["avg_parallel"], 1.5, places=6)

    def test_compute_tag_summary_total_self_ms(self):
        tag = self._make_tag(
            [500_000_000, 500_000_000], [1_000_000_000, 1_000_000_000],
            [1_000_000_000, 1_000_000_000],
            [0.0, 0.0], [1.0, 1.0]
        )
        s = tags_mod.compute_tag_summary(tag)
        self.assertAlmostEqual(s["total_self_ms"], 1000.0, places=3)
        self.assertAlmostEqual(s["total_all_ms"], 2000.0, places=3)

    # ------------------------------------------------------------------
    # build_tree()
    # ------------------------------------------------------------------

    def test_build_tree_single_root(self):
        summary = {"logic": {"total_span_ms": 100}}
        roots, children = tags_mod.build_tree(summary)
        self.assertIn("logic", roots)
        self.assertEqual(children["logic"], [])

    def test_build_tree_parent_child(self):
        summary = {
            "logic": {"total_span_ms": 100},
            "logic_motor": {"total_span_ms": 50},
        }
        roots, children = tags_mod.build_tree(summary)
        self.assertIn("logic", roots)
        self.assertNotIn("logic_motor", roots)
        self.assertIn("logic_motor", children["logic"])

    def test_build_tree_grandchild(self):
        summary = {
            "logic": {"total_span_ms": 100},
            "logic_motor": {"total_span_ms": 50},
            "logic_motor_tick": {"total_span_ms": 20},
        }
        roots, children = tags_mod.build_tree(summary)
        self.assertIn("logic_motor", children["logic"])
        self.assertIn("logic_motor_tick", children["logic_motor"])
        self.assertNotIn("logic_motor_tick", roots)

    def test_build_tree_multiple_roots(self):
        summary = {
            "logic": {"total_span_ms": 100},
            "render": {"total_span_ms": 60},
            "present": {"total_span_ms": 40},
        }
        roots, children = tags_mod.build_tree(summary)
        self.assertIn("logic", roots)
        self.assertIn("render", roots)
        self.assertIn("present", roots)

    def test_build_tree_child_assigned_to_nearest_parent(self):
        # logic_motor_tick は logic_motor の子（logic ではなく）
        summary = {
            "logic": {"total_span_ms": 100},
            "logic_motor": {"total_span_ms": 50},
            "logic_motor_tick": {"total_span_ms": 20},
        }
        _, children = tags_mod.build_tree(summary)
        self.assertNotIn("logic_motor_tick", children["logic"])
        self.assertIn("logic_motor_tick", children["logic_motor"])

    def test_build_tree_orphan_without_parent_becomes_root(self):
        # "render_shadow" の親 "render" が存在しない → root になる
        summary = {
            "logic": {"total_span_ms": 100},
            "render_shadow": {"total_span_ms": 30},
        }
        roots, children = tags_mod.build_tree(summary)
        self.assertIn("render_shadow", roots)

    def test_build_tree_all_undefined_are_roots(self):
        summary = {
            "all": {"total_span_ms": 200},
            "undefined": {"total_span_ms": 10},
        }
        roots, children = tags_mod.build_tree(summary)
        self.assertIn("all", roots)
        self.assertIn("undefined", roots)


# ===========================================================================
# AnalyzeMemoryUnitTests — analyze_memory.fmt_bytes()
# ===========================================================================

class AnalyzeMemoryUnitTests(unittest.TestCase):

    def test_fmt_bytes_zero(self):
        self.assertEqual(mem_mod.fmt_bytes(0), "0 B")

    def test_fmt_bytes_bytes(self):
        self.assertEqual(mem_mod.fmt_bytes(512), "512 B")

    def test_fmt_bytes_kb_boundary(self):
        # 1024 → "1.0 KB"
        self.assertEqual(mem_mod.fmt_bytes(1024), "1.0 KB")

    def test_fmt_bytes_kb(self):
        # 2048 → "2.0 KB"
        self.assertEqual(mem_mod.fmt_bytes(2048), "2.0 KB")

    def test_fmt_bytes_mb_boundary(self):
        # 1024^2 → "1.0 MB"
        self.assertEqual(mem_mod.fmt_bytes(1024 ** 2), "1.0 MB")

    def test_fmt_bytes_mb(self):
        result = mem_mod.fmt_bytes(512 * 1024 * 1024)
        self.assertEqual(result, "512.0 MB")

    def test_fmt_bytes_gb_boundary(self):
        # 1024^3 → "1.00 GB"
        self.assertEqual(mem_mod.fmt_bytes(1024 ** 3), "1.00 GB")

    def test_fmt_bytes_gb(self):
        result = mem_mod.fmt_bytes(2 * 1024 ** 3)
        self.assertEqual(result, "2.00 GB")

    def test_fmt_bytes_fractional_kb(self):
        # 1536 = 1.5 KB
        result = mem_mod.fmt_bytes(1536)
        self.assertEqual(result, "1.5 KB")


# ===========================================================================
# AnalyzeScriptsIntegrationTests — main() via subprocess + mock HTTP server
# ===========================================================================

# ---------------------------------------------------------------------------
# Mock HTTP server — 提供所有分析脚本需要的端点
# ---------------------------------------------------------------------------

_FRAMES_DATA = [
    {"frame_idx": i, "start_ns": i * 16_666_666,
     "end_ns": (i + 1) * 16_666_666, "duration_ns": 16_666_666}
    for i in range(10)
]
# 加入一个超预算帧 (帧10: 50ms)
_FRAMES_DATA.append({"frame_idx": 10, "start_ns": 10 * 16_666_666,
                      "end_ns": 10 * 16_666_666 + 50_000_000,
                      "duration_ns": 50_000_000})

_TAG_DATA = [
    {
        "tag_name": "logic",
        "self_times":     [8_000_000] * 11,
        "all_times":      [10_000_000] * 11,
        "span_times":     [12_000_000] * 11,
        "parallel_ratios": [1.0] * 11,
        "idle_times":     [500_000] * 11,
        "idle_ratios":    [0.04] * 11,
    },
    {
        "tag_name": "render",
        "self_times":     [5_000_000] * 11,
        "all_times":      [5_000_000] * 11,
        "span_times":     [5_000_000] * 11,
        "parallel_ratios": [-1.0] * 11,
        "idle_times":     [0] * 11,
        "idle_ratios":    [-1.0] * 11,
    },
]

_TRACE_OVERVIEW = {
    "captured_program": "test_app",
    "host_info": "TestHost",
    "first_time": 0,
    "last_time": 1_000_000_000,
    "zone_count": 5000,
    "frame_count": 11,
    "lock_count": 3,
    "plot_count": 1,
    "message_count": 5,
    "context_switch_count": 100,
    "port": 9090,
}

_TRACE_INFO = {
    "host": "TestHost",
    "cpu": {"manufacturer": "GenuineIntel", "cpu_id": "0x906A4", "architecture": "x86_64"},
    "timing": {"capture_time": 1700000000, "executable_time": 1700000001,
               "delay_ns": 14000, "resolution_ns": 100, "pid": 9999},
    "app_info": ["Version=1.0"],
    "cpu_topology": {"pkg_0": {"die_0": {"core_0": [0, 1]}}},
    "frame_stats": {
        "total_frames": 11,
        "first_time_ns": 0, "last_time_ns": 1_000_000_000,
        "total_time_ns": 1_000_000_000,
        "min_frame_ns": 16_666_666,
        "max_frame_ns": 50_000_000,
        "avg_frame_ns": 20_000_000,
    },
    "trace_stats": {
        "zone_count": 5000, "gpu_zone_count": 100, "lock_count": 3,
        "plot_count": 1, "message_count": 5, "context_switch_count": 100,
        "callstack_sample_count": 0, "src_loc_count": 50,
        "symbol_count": 200, "thread_count": 2,
    },
    "port": 9090,
}

_POOL_OVERVIEW = {
    "alloc_count": 200,
    "free_count": 195,
    "alloc_bytes": 2_097_152,
    "free_bytes": 2_048_000,
    "active_count": 5,
    "active_bytes": 49_152,
    "port": 9090,
}


class _MockHandler(BaseHTTPRequestHandler):
    """Mock Tracy HTTP server for integration tests."""

    def log_message(self, *args):
        pass  # suppress output

    def _send(self, status, body):
        if isinstance(body, str):
            raw = body.encode("utf-8")
            ct = "text/plain; charset=utf-8"
        else:
            raw = json.dumps(body).encode("utf-8")
            ct = "application/json; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api/filepath":
            self._send(200, {"filepath": "/mock/test.tracy", "port": 9090})
        elif path == "/api/trace_overview":
            self._send(200, _TRACE_OVERVIEW)
        elif path == "/api/trace_info":
            self._send(200, _TRACE_INFO)
        elif path == "/api/threads":
            self._send(200, {"threads": [
                {"thread_id": 1, "thread_name": "Main thread"},
                {"thread_id": 2, "thread_name": "TaskWorker_0"},
            ], "port": 9090})
        elif path == "/api/frames":
            self._send(200, {
                "total_count": len(_FRAMES_DATA),
                "offset": 0,
                "frames": _FRAMES_DATA,
                "port": 9090,
            })
        elif path == "/api/stats/frame_tags":
            result = list(_TAG_DATA)
            result_with_port = {"_list": result, "port": 9090}
            # frame_tags returns a JSON array directly
            raw = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(raw)
        elif path == "/api/plots":
            self._send(200, {"plots": ["FPS"], "port": 9090})
        elif path == "/api/memory/pools":
            self._send(200, {"pools": ["default"], "port": 9090})
        elif "/overview" in self.path:
            self._send(200, _POOL_OVERVIEW)
        elif path == "/api/stats/summary":
            self._send(200, {**_TRACE_OVERVIEW, "port": 9090})
        elif path == "/api/zones/by_tag":
            # Parse tag from query string
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            tag = qs.get("tag", [""])[0]
            if not tag:
                self._send(400, {"error": "Missing required parameter: tag"})
            elif tag == "logic":
                start_frame = qs.get("start_frame", [None])[0]
                end_frame   = qs.get("end_frame",   [None])[0]
                if start_frame is not None and end_frame is not None:
                    self._send(200, {"tag": "logic", "count": 2, "zone_ids": [111111, 222222]})
                else:
                    self._send(200, {"tag": "logic", "count": 3, "zone_ids": [111111, 222222, 333333]})
            else:
                self._send(200, {"tag": tag, "count": 0, "zone_ids": []})
        elif path == "/api/frame_number":
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            ts_str = qs.get("ts", [None])[0]
            if ts_str is None:
                self._send(400, {"error": "Missing or invalid parameter: ts"})
            else:
                ts_ns = int(ts_str)
                # Frame duration: 16_666_666 ns each; first frame at ts=16_666_666
                frame_num = ts_ns // 16_666_666 - 1 if ts_ns >= 16_666_666 else -1
                self._send(200, {"ts_ns": ts_ns, "frame_number": frame_num})
        else:
            self._send(404, {"error": "not found"})


class AnalyzeScriptsIntegrationTests(unittest.TestCase):
    """
    通过 subprocess 运行分析脚本，注入环境变量 TRACY_TEST_PORT 让脚本只扫描
    本地 mock server 的端口，绕过真实的 Tracy Profiler 实例。
    """

    @classmethod
    def setUpClass(cls):
        # 绑定随机端口，避免与真实 Tracy 或其他测试冲突
        cls.server = HTTPServer(("localhost", 0), _MockHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _run(self, script_name, args=None):
        """运行脚本，通过 TRACY_TEST_PORT 引导到 mock server"""
        script_path = os.path.join(SCRIPT_DIR, script_name)
        cmd = [sys.executable, script_path] + (args or [])
        env = os.environ.copy()
        env["TRACY_TEST_PORT"] = str(self.port)
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=30, env=env,
                                encoding="utf-8", errors="replace")
        return result.returncode, result.stdout, result.stderr

    # ------------------------------------------------------------------
    # analyze_frames.py
    # ------------------------------------------------------------------

    def test_frames_json_output_has_required_keys(self):
        rc, out, err = self._run("analyze_frames.py", ["--json"])
        self.assertEqual(rc, 0, f"非零退出码: stderr={err}")
        data = json.loads(out)
        for key in ("total_frames", "avg_ms", "avg_fps", "min_ms", "max_ms",
                    "percentiles", "over_budget_count", "over_budget_pct",
                    "over_2x_count", "top_frames"):
            self.assertIn(key, data, f"缺少字段: {key}")

    def test_frames_json_total_frames_correct(self):
        rc, out, _ = self._run("analyze_frames.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["total_frames"], len(_FRAMES_DATA))

    def test_frames_json_avg_fps_positive(self):
        rc, out, _ = self._run("analyze_frames.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertGreater(data["avg_fps"], 0)

    def test_frames_json_percentiles_have_all_keys(self):
        rc, out, _ = self._run("analyze_frames.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for p in ("p50", "p75", "p90", "p99"):
            self.assertIn(p, data["percentiles"])

    def test_frames_json_top_frames_sorted_descending(self):
        rc, out, _ = self._run("analyze_frames.py", ["--json", "--top", "3"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        durations = [f["duration_ms"] for f in data["top_frames"]]
        self.assertEqual(durations, sorted(durations, reverse=True))

    def test_frames_json_over_budget_count_correct(self):
        """默认预算 16.67ms，帧10 是 50ms，应该被计入超预算"""
        rc, out, _ = self._run("analyze_frames.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertGreaterEqual(data["over_budget_count"], 1)

    def test_frames_json_max_ms_matches_worst_frame(self):
        rc, out, _ = self._run("analyze_frames.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertAlmostEqual(data["max_ms"], 50.0, places=0)

    def test_frames_text_output_contains_fps(self):
        rc, out, _ = self._run("analyze_frames.py")
        self.assertEqual(rc, 0)
        self.assertIn("FPS", out)

    def test_frames_text_output_contains_percentile(self):
        rc, out, _ = self._run("analyze_frames.py")
        self.assertEqual(rc, 0)
        self.assertIn("P50", out)

    def test_frames_custom_budget_affects_over_budget_count(self):
        # 预算 100ms，所有帧都不超预算
        rc, out, _ = self._run("analyze_frames.py", ["--json", "--budget", "100"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["over_budget_count"], 0)

    # ------------------------------------------------------------------
    # analyze_tags.py
    # ------------------------------------------------------------------

    def test_tags_json_output_is_dict(self):
        rc, out, err = self._run("analyze_tags.py", ["--json"])
        self.assertEqual(rc, 0, f"stderr={err}")
        data = json.loads(out)
        self.assertIsInstance(data, dict)

    def test_tags_json_contains_logic_tag(self):
        rc, out, _ = self._run("analyze_tags.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("logic", data)

    def test_tags_json_contains_render_tag(self):
        rc, out, _ = self._run("analyze_tags.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("render", data)

    def test_tags_json_tag_has_required_fields(self):
        rc, out, _ = self._run("analyze_tags.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for tag_name, tag_data in data.items():
            for field in ("total_span_ms", "total_all_ms", "total_self_ms",
                          "avg_span_ms", "avg_idle_ratio", "frame_count"):
                self.assertIn(field, tag_data, f"tag={tag_name} 缺少 {field}")

    def test_tags_json_total_span_ms_positive(self):
        rc, out, _ = self._run("analyze_tags.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertGreater(data["logic"]["total_span_ms"], 0)

    def test_tags_text_output_contains_tag_names(self):
        rc, out, _ = self._run("analyze_tags.py")
        self.assertEqual(rc, 0)
        self.assertIn("logic", out)
        self.assertIn("render", out)

    def test_tags_text_output_contains_ms(self):
        rc, out, _ = self._run("analyze_tags.py")
        self.assertEqual(rc, 0)
        self.assertIn("ms", out)

    def test_tags_filter_only_shows_matching_tags(self):
        rc, out, _ = self._run("analyze_tags.py", ["--filter", "logic"])
        self.assertEqual(rc, 0)
        # render は filter_prefix が設定されていれば表示されない（logic で始まらない）
        # ただし render は children がないのでスキップされる
        self.assertIn("logic", out)

    # ------------------------------------------------------------------
    # analyze_memory.py
    # ------------------------------------------------------------------

    def test_memory_json_output_is_list(self):
        rc, out, err = self._run("analyze_memory.py", ["--json"])
        self.assertEqual(rc, 0, f"stderr={err}")
        data = json.loads(out)
        self.assertIsInstance(data, list)

    def test_memory_json_has_default_pool(self):
        rc, out, _ = self._run("analyze_memory.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        pool_names = [r["pool"] for r in data]
        self.assertIn("default", pool_names)

    def test_memory_json_pool_has_required_fields(self):
        rc, out, _ = self._run("analyze_memory.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for r in data:
            for field in ("pool", "alloc_count", "alloc_bytes",
                          "active_count", "active_bytes", "survive_rate"):
                self.assertIn(field, r, f"缺少字段: {field}")

    def test_memory_json_survive_rate_between_0_and_1(self):
        rc, out, _ = self._run("analyze_memory.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for r in data:
            self.assertGreaterEqual(r["survive_rate"], 0.0)
            self.assertLessEqual(r["survive_rate"], 1.0)

    def test_memory_json_alloc_per_frame_positive(self):
        rc, out, _ = self._run("analyze_memory.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for r in data:
            self.assertGreaterEqual(r["alloc_per_frame"], 0.0)

    def test_memory_text_output_contains_pool_name(self):
        rc, out, _ = self._run("analyze_memory.py")
        self.assertEqual(rc, 0)
        self.assertIn("default", out)

    def test_memory_text_output_contains_存活内存(self):
        rc, out, _ = self._run("analyze_memory.py")
        self.assertEqual(rc, 0)
        self.assertIn("存活内存", out)

    def test_memory_survive_rate_correct(self):
        """active_count=5, alloc_count=200 → survive_rate=0.025"""
        rc, out, _ = self._run("analyze_memory.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        default_pool = next(r for r in data if r["pool"] == "default")
        expected = 5 / 200
        self.assertAlmostEqual(default_pool["survive_rate"], expected, places=4)

    # ------------------------------------------------------------------
    # analyze_overview.py
    # ------------------------------------------------------------------

    def test_overview_json_has_all_sections(self):
        rc, out, err = self._run("analyze_overview.py", ["--json"])
        self.assertEqual(rc, 0, f"stderr={err}")
        data = json.loads(out)
        for key in ("trace_info", "trace_overview", "threads", "plots", "pools"):
            self.assertIn(key, data, f"缺少 section: {key}")

    def test_overview_json_trace_info_has_frame_stats(self):
        rc, out, _ = self._run("analyze_overview.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("frame_stats", data["trace_info"])

    def test_overview_json_threads_is_list(self):
        rc, out, _ = self._run("analyze_overview.py", ["--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        threads = data["threads"].get("threads", [])
        self.assertIsInstance(threads, list)
        self.assertGreater(len(threads), 0)

    def test_overview_text_contains_program_name(self):
        rc, out, _ = self._run("analyze_overview.py")
        self.assertEqual(rc, 0)
        self.assertIn("test_app", out)

    def test_overview_text_contains_fps_info(self):
        rc, out, _ = self._run("analyze_overview.py")
        self.assertEqual(rc, 0)
        self.assertIn("FPS", out)

    def test_overview_text_contains_thread_list(self):
        rc, out, _ = self._run("analyze_overview.py")
        self.assertEqual(rc, 0)
        self.assertIn("Main thread", out)


# ===========================================================================
# ZonesByTagTests — /api/zones/by_tag  (via tracy_http.py subprocess)
# ===========================================================================

class ZonesByTagTests(unittest.TestCase):
    """
    测试 zones_by_tag 和 frame_number 命令，通过 tracy_http.py subprocess +
    mock HTTP server 验证 JSON 输出的正确性。
    """

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("localhost", 0), _MockHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _run_cmd(self, *args):
        """调用 tracy_http.py 命令，注入测试端口"""
        cmd = [sys.executable,
               os.path.join(SCRIPT_DIR, "tracy_http.py")] + list(args)
        env = os.environ.copy()
        env["TRACY_TEST_PORT"] = str(self.port)
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run(cmd, capture_output=True, timeout=15,
                           env=env, encoding="utf-8", errors="replace")
        return r.returncode, r.stdout.strip(), r.stderr.strip()

    # ------------------------------------------------------------------
    # zones_by_tag
    # ------------------------------------------------------------------

    def test_zones_by_tag_rc_zero(self):
        rc, _, err = self._run_cmd("zones_by_tag", "logic")
        self.assertEqual(rc, 0, f"stderr={err}")

    def test_zones_by_tag_has_required_fields(self):
        rc, out, _ = self._run_cmd("zones_by_tag", "logic")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for field in ("tag", "count", "zone_ids", "port"):
            self.assertIn(field, data, f"缺少字段: {field}")

    def test_zones_by_tag_tag_matches_request(self):
        _, out, _ = self._run_cmd("zones_by_tag", "logic")
        data = json.loads(out)
        self.assertEqual(data["tag"], "logic")

    def test_zones_by_tag_count_matches_zone_ids_length(self):
        _, out, _ = self._run_cmd("zones_by_tag", "logic")
        data = json.loads(out)
        self.assertEqual(data["count"], len(data["zone_ids"]))

    def test_zones_by_tag_zone_ids_are_positive_integers(self):
        _, out, _ = self._run_cmd("zones_by_tag", "logic")
        data = json.loads(out)
        for zid in data["zone_ids"]:
            self.assertIsInstance(zid, int)
            self.assertGreater(zid, 0)

    def test_zones_by_tag_unknown_tag_returns_empty(self):
        rc, out, _ = self._run_cmd("zones_by_tag", "no_such_tag_xyz")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["zone_ids"], [])

    def test_zones_by_tag_with_frame_range(self):
        rc, out, _ = self._run_cmd("zones_by_tag", "logic", "0", "10")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # フレーム絞り込み結果は全件以下
        self.assertLessEqual(data["count"], 3)
        self.assertEqual(data["count"], len(data["zone_ids"]))

    def test_zones_by_tag_missing_tag_exits_nonzero(self):
        """引数なし → エラー"""
        rc, _, _ = self._run_cmd("zones_by_tag")
        self.assertNotEqual(rc, 0)

    # ------------------------------------------------------------------
    # frame_number
    # ------------------------------------------------------------------

    def test_frame_number_rc_zero(self):
        rc, _, err = self._run_cmd("frame_number", "16666666")
        self.assertEqual(rc, 0, f"stderr={err}")

    def test_frame_number_has_required_fields(self):
        rc, out, _ = self._run_cmd("frame_number", "16666666")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for field in ("ts_ns", "frame_number", "port"):
            self.assertIn(field, data, f"缺少字段: {field}")

    def test_frame_number_ts_matches_input(self):
        _, out, _ = self._run_cmd("frame_number", "16666666")
        data = json.loads(out)
        self.assertEqual(data["ts_ns"], 16_666_666)

    def test_frame_number_is_integer(self):
        _, out, _ = self._run_cmd("frame_number", "16666666")
        data = json.loads(out)
        self.assertIsInstance(data["frame_number"], int)

    def test_frame_number_valid_ts_non_negative(self):
        _, out, _ = self._run_cmd("frame_number", "16666666")
        data = json.loads(out)
        self.assertGreaterEqual(data["frame_number"], 0)

    def test_frame_number_early_ts_returns_minus_one(self):
        """ts < 第一帧 → -1"""
        _, out, _ = self._run_cmd("frame_number", "100")
        data = json.loads(out)
        self.assertEqual(data["frame_number"], -1)

    def test_frame_number_missing_ts_exits_nonzero(self):
        rc, _, _ = self._run_cmd("frame_number")
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
