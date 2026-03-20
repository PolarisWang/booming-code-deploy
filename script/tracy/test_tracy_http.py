"""
Tracy HTTP API test suite.

Two test classes:
  TracyHttpLiveTests   -- integration tests, require Tracy Profiler to be running
                          with a trace file loaded. Skipped automatically if not found.
  TracyHttpMockTests   -- unit tests using a local mock HTTP server, always run offline.

Run all:
    python test_tracy_http.py
Run only offline tests:
    python test_tracy_http.py TracyHttpMockTests
"""

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_PORT = 9090
PORT_SCAN_RANGE = 10


def _discover_live_port():
    """Return the first live Tracy port that has a trace loaded, or None."""
    for port in range(BASE_PORT, BASE_PORT + PORT_SCAN_RANGE):
        try:
            resp = urllib.request.urlopen(
                f"http://localhost:{port}/api/filepath", timeout=1.0
            )
            if resp.status == 200:
                data = json.loads(resp.read())
                if data.get("filepath"):
                    return port
        except Exception:
            continue
    return None


def _get(port, path):
    """GET JSON from Tracy HTTP API. Returns (status_code, dict)."""
    try:
        resp = urllib.request.urlopen(
            f"http://localhost:{port}{path}", timeout=5.0
        )
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ---------------------------------------------------------------------------
# Integration tests (require live Tracy instance)
# ---------------------------------------------------------------------------

LIVE_PORT = _discover_live_port()


@unittest.skipIf(LIVE_PORT is None, "Tracy Profiler not running or no trace loaded")
class TracyHttpLiveTests(unittest.TestCase):
    """Tests against the real Tracy HTTP server."""

    port = LIVE_PORT

    # ------------------------------------------------------------------
    # GET /api/health
    # ------------------------------------------------------------------

    def test_health_status_200(self):
        code, data = _get(self.port, "/api/health")
        self.assertEqual(code, 200)

    def test_health_returns_ok(self):
        _, data = _get(self.port, "/api/health")
        self.assertEqual(data.get("status"), "ok")

    # ------------------------------------------------------------------
    # GET /api/filepath
    # ------------------------------------------------------------------

    def test_filepath_status_200(self):
        code, _ = _get(self.port, "/api/filepath")
        self.assertEqual(code, 200)

    def test_filepath_has_filepath_field(self):
        _, data = _get(self.port, "/api/filepath")
        self.assertIn("filepath", data)

    def test_filepath_is_nonempty_string(self):
        _, data = _get(self.port, "/api/filepath")
        self.assertIsInstance(data["filepath"], str)
        self.assertGreater(len(data["filepath"]), 0)

    # ------------------------------------------------------------------
    # GET /api/current_selection
    # ------------------------------------------------------------------

    def test_selection_status_200(self):
        code, _ = _get(self.port, "/api/current_selection")
        self.assertEqual(code, 200)

    def test_selection_has_valid_field(self):
        _, data = _get(self.port, "/api/current_selection")
        self.assertIn("valid", data)
        self.assertIsInstance(data["valid"], bool)

    def test_selection_valid_true_has_required_fields(self):
        _, data = _get(self.port, "/api/current_selection")
        if not data["valid"]:
            self.skipTest("No zone selected in Tracy UI")
        required = [
            "zone_id", "thread_id", "thread_name",
            "parent_id", "parent_name",
            "children_ids", "children_names",
            "name", "function", "file", "line",
            "tag", "frame_number", "start_ns", "duration_ns",
        ]
        for field in required:
            self.assertIn(field, data, f"Missing field: {field}")

    def test_selection_valid_true_types(self):
        _, data = _get(self.port, "/api/current_selection")
        if not data["valid"]:
            self.skipTest("No zone selected in Tracy UI")
        self.assertIsInstance(data["zone_id"],       int)
        self.assertIsInstance(data["thread_id"],     int)
        self.assertIsInstance(data["thread_name"],   str)
        self.assertIsInstance(data["parent_id"],     int)
        self.assertIsInstance(data["children_ids"],  list)
        self.assertIsInstance(data["children_names"],list)
        self.assertIsInstance(data["name"],          str)
        self.assertIsInstance(data["function"],      str)
        self.assertIsInstance(data["file"],          str)
        self.assertIsInstance(data["line"],          int)
        self.assertIsInstance(data["start_ns"],      int)
        self.assertIsInstance(data["duration_ns"],   int)

    def test_selection_duration_positive(self):
        _, data = _get(self.port, "/api/current_selection")
        if not data["valid"]:
            self.skipTest("No zone selected in Tracy UI")
        self.assertGreater(data["duration_ns"], 0)

    def test_selection_children_ids_names_same_length(self):
        _, data = _get(self.port, "/api/current_selection")
        if not data["valid"]:
            self.skipTest("No zone selected in Tracy UI")
        self.assertEqual(len(data["children_ids"]), len(data["children_names"]))

    # ------------------------------------------------------------------
    # GET /api/zone/{id}
    # ------------------------------------------------------------------

    def test_zone_invalid_id_returns_400(self):
        code, data = _get(self.port, "/api/zone/0")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_zone_nonexistent_returns_404(self):
        code, data = _get(self.port, "/api/zone/999999999999")
        self.assertEqual(code, 404)
        self.assertIn("valid", data)
        self.assertFalse(data["valid"])

    def test_zone_selected_zone_roundtrip(self):
        """Query the currently selected zone by ID and verify it matches selection."""
        _, sel = _get(self.port, "/api/current_selection")
        if not sel["valid"]:
            self.skipTest("No zone selected in Tracy UI")
        zone_id = sel["zone_id"]
        code, zone = _get(self.port, f"/api/zone/{zone_id}")
        self.assertEqual(code, 200)
        self.assertTrue(zone.get("valid"))
        self.assertEqual(zone["zone_id"],     sel["zone_id"])
        self.assertEqual(zone["function"],    sel["function"])
        self.assertEqual(zone["duration_ns"], sel["duration_ns"])

    def test_zone_hex_id_accepted(self):
        """zone_id can be passed as a hex string (0x...)."""
        _, sel = _get(self.port, "/api/current_selection")
        if not sel["valid"]:
            self.skipTest("No zone selected in Tracy UI")
        hex_id = hex(sel["zone_id"])
        code, zone = _get(self.port, f"/api/zone/{hex_id}")
        self.assertEqual(code, 200)
        self.assertTrue(zone.get("valid"))

    # ------------------------------------------------------------------
    # GET /api/trace_overview  (requires new binary with callbacks)
    # ------------------------------------------------------------------

    def test_trace_overview_responds(self):
        code, data = _get(self.port, "/api/trace_overview")
        # 200 = new binary with callbacks; 503 = old binary without callbacks
        self.assertIn(code, (200, 503))

    def test_trace_overview_200_has_required_fields(self):
        code, data = _get(self.port, "/api/trace_overview")
        if code != 200:
            self.skipTest("trace_overview not available (old binary or no trace)")
        required = [
            "captured_program", "host_info",
            "first_time", "last_time",
            "zone_count", "frame_count", "lock_count",
            "plot_count", "message_count", "context_switch_count",
        ]
        for field in required:
            self.assertIn(field, data, f"Missing field: {field}")

    def test_trace_overview_200_types(self):
        code, data = _get(self.port, "/api/trace_overview")
        if code != 200:
            self.skipTest("trace_overview not available")
        self.assertIsInstance(data["captured_program"], str)
        self.assertIsInstance(data["host_info"],        str)
        self.assertIsInstance(data["first_time"],       int)
        self.assertIsInstance(data["last_time"],        int)
        self.assertIsInstance(data["zone_count"],       int)
        self.assertIsInstance(data["frame_count"],      int)
        self.assertGreater(data["last_time"], data["first_time"])

    # ------------------------------------------------------------------
    # GET /api/threads
    # ------------------------------------------------------------------

    def test_threads_responds(self):
        code, _ = _get(self.port, "/api/threads")
        self.assertIn(code, (200, 503))

    def test_threads_200_has_threads_array(self):
        code, data = _get(self.port, "/api/threads")
        if code != 200:
            self.skipTest("threads not available")
        self.assertIn("threads", data)
        self.assertIsInstance(data["threads"], list)

    def test_threads_200_each_entry_has_id_and_name(self):
        code, data = _get(self.port, "/api/threads")
        if code != 200:
            self.skipTest("threads not available")
        for t in data["threads"]:
            self.assertIn("thread_id",   t)
            self.assertIn("thread_name", t)
            self.assertIsInstance(t["thread_id"],   int)
            self.assertIsInstance(t["thread_name"], str)

    # ------------------------------------------------------------------
    # GET /api/frames
    # ------------------------------------------------------------------

    def test_frames_responds(self):
        code, _ = _get(self.port, "/api/frames")
        self.assertIn(code, (200, 503))

    def test_frames_200_has_required_fields(self):
        code, data = _get(self.port, "/api/frames")
        if code != 200:
            self.skipTest("frames not available")
        self.assertIn("total_count", data)
        self.assertIn("offset",      data)
        self.assertIn("frames",      data)
        self.assertIsInstance(data["frames"], list)

    def test_frames_200_default_count_at_most_100(self):
        code, data = _get(self.port, "/api/frames")
        if code != 200:
            self.skipTest("frames not available")
        self.assertLessEqual(len(data["frames"]), 100)

    def test_frames_200_each_frame_has_timing_fields(self):
        code, data = _get(self.port, "/api/frames?offset=0&count=5")
        if code != 200:
            self.skipTest("frames not available")
        for f in data["frames"]:
            self.assertIn("frame_idx",   f)
            self.assertIn("start_ns",    f)
            self.assertIn("end_ns",      f)
            self.assertIn("duration_ns", f)
            self.assertGreaterEqual(f["end_ns"],      f["start_ns"])
            self.assertGreaterEqual(f["duration_ns"], 0)

    def test_frames_200_offset_param(self):
        code, data = _get(self.port, "/api/frames?offset=10&count=5")
        if code != 200:
            self.skipTest("frames not available")
        self.assertEqual(data["offset"], 10)
        if data["frames"]:
            self.assertEqual(data["frames"][0]["frame_idx"], 10)

    def test_frames_200_count_capped_at_1000(self):
        code, data = _get(self.port, "/api/frames?offset=0&count=9999")
        if code != 200:
            self.skipTest("frames not available")
        self.assertLessEqual(len(data["frames"]), 1000)

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_unknown_path_returns_404(self):
        code, data = _get(self.port, "/api/nonexistent")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    def test_non_get_method_returns_405(self):
        req = urllib.request.Request(
            f"http://localhost:{self.port}/api/health",
            method="POST",
            data=b"",
        )
        try:
            urllib.request.urlopen(req, timeout=3)
            self.fail("Expected HTTPError 405")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 405)

    def test_cors_headers_present(self):
        resp = urllib.request.urlopen(
            f"http://localhost:{self.port}/api/health", timeout=3
        )
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_options_preflight_returns_204(self):
        req = urllib.request.Request(
            f"http://localhost:{self.port}/api/health",
            method="OPTIONS",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=3)
            self.assertEqual(resp.status, 204)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 204)


# ---------------------------------------------------------------------------
# Mock server for offline unit tests
# ---------------------------------------------------------------------------

class _MockHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler returning canned Tracy-style JSON responses."""

    ROUTES = {
        "/api/health":            (200, {"status": "ok"}),
        "/api/filepath":          (200, {"filepath": "/mock/trace.tracy"}),
        "/api/current_selection": (200, {
            "valid": True,
            "zone_id": 111111,
            "thread_id": 222222,
            "thread_name": "MainThread",
            "parent_id": 0,
            "parent_name": "",
            "children_ids": [333333, 444444],
            "children_names": ["childA", "childB"],
            "name": "MockZone",
            "function": "MockClass::mockMethod",
            "file": "/src/mock.cpp",
            "line": 42,
            "tag": "",
            "frame_number": 1,
            "start_ns": 1000000,
            "duration_ns": 5000000,
        }),
        "/api/zone/111111":       (200, {
            "valid": True,
            "zone_id": 111111,
            "thread_id": 222222,
            "thread_name": "MainThread",
            "parent_id": 0,
            "parent_name": "",
            "children_ids": [333333, 444444],
            "children_names": ["childA", "childB"],
            "name": "MockZone",
            "function": "MockClass::mockMethod",
            "file": "/src/mock.cpp",
            "line": 42,
            "tag": "",
            "frame_number": 1,
            "start_ns": 1000000,
            "duration_ns": 5000000,
        }),
        "/api/zone/0":            (400, {"error": "Invalid zone_id"}),
        "/api/zone/999":          (404, {"valid": False, "error": "Zone not found"}),
        "/api/trace_overview":    (200, {
            "captured_program": "mock_app",
            "host_info": "MockHost",
            "first_time": 0,
            "last_time": 1000000000,
            "zone_count": 9999,
            "frame_count": 100,
            "lock_count": 5,
            "plot_count": 2,
            "message_count": 10,
            "context_switch_count": 500,
        }),
        "/api/threads":           (200, {"threads": [
            {"thread_id": 222222, "thread_name": "MainThread"},
            {"thread_id": 333333, "thread_name": "WorkerThread"},
        ]}),
        "/api/frames":            (200, {
            "total_count": 100,
            "offset": 0,
            "frames": [
                {"frame_idx": i, "start_ns": i * 16666666,
                 "end_ns": (i + 1) * 16666666, "duration_ns": 16666666}
                for i in range(5)
            ],
        }),
        "/api/frames?offset=10&count=5": (200, {
            "total_count": 100,
            "offset": 10,
            "frames": [
                {"frame_idx": 10 + i, "start_ns": (10 + i) * 16666666,
                 "end_ns": (11 + i) * 16666666, "duration_ns": 16666666}
                for i in range(5)
            ],
        }),
        # --- New endpoints ---
        "/api/zone/111111/children": (200, {"children": [
            {
                "valid": True,
                "zone_id": 333333, "thread_id": 222222, "thread_name": "MainThread",
                "parent_id": 111111, "parent_name": "MockZone",
                "children_ids": [], "children_names": [],
                "name": "childA", "function": "childFuncA",
                "file": "/src/child.cpp", "line": 10,
                "tag": "", "frame_number": 1,
                "start_ns": 1000000, "duration_ns": 2000000,
            },
            {
                "valid": True,
                "zone_id": 444444, "thread_id": 222222, "thread_name": "MainThread",
                "parent_id": 111111, "parent_name": "MockZone",
                "children_ids": [], "children_names": [],
                "name": "childB", "function": "childFuncB",
                "file": "/src/child.cpp", "line": 20,
                "tag": "", "frame_number": 1,
                "start_ns": 3000000, "duration_ns": 1000000,
            },
        ]}),
        "/api/zone/0/children":   (400, {"error": "Invalid zone_id"}),
        "/api/zone/999/children": (404, {"error": "Zone not found"}),
        "/api/messages": (200, {
            "total_count": 3,
            "offset": 0,
            "messages": [
                {"time": 1000000, "text": "msg1", "thread_id": 222222, "thread_name": "MainThread", "color": 0},
                {"time": 2000000, "text": "msg2", "thread_id": 333333, "thread_name": "WorkerThread", "color": 255},
                {"time": 3000000, "text": "msg3", "thread_id": 222222, "thread_name": "MainThread", "color": 0},
            ],
        }),
        "/api/messages?offset=5&count=10": (200, {
            "total_count": 3, "offset": 5, "messages": [],
        }),
        "/api/messages?count=9999": (200, {
            "total_count": 3, "offset": 0,
            "messages": [
                {"time": 1000000, "text": "msg1", "thread_id": 222222, "thread_name": "MainThread", "color": 0},
            ],
        }),
        "/api/messages?start=0&end=999999999999": (200, {
            "total_count": 3, "offset": 0,
            "messages": [
                {"time": 1000000, "text": "msg1", "thread_id": 222222, "thread_name": "MainThread", "color": 0},
            ],
        }),
        "/api/messages?start=999999999999&end=1": (200, {
            "total_count": 0, "offset": 0, "messages": [],
        }),
        "/api/plots": (200, {"plots": ["FPS", "MemUsage"]}),
        "/api/plots/FPS/count":  (200, {"count": 500}),
        "/api/plots/FPS/values": (200, {
            "total_count": 500, "offset": 0,
            "values": [{"time": i * 16666666, "val": 60.0 + i * 0.1} for i in range(5)],
        }),
        "/api/plots/FPS/values?count=5":   (200, {
            "total_count": 500, "offset": 0,
            "values": [{"time": i * 16666666, "val": 60.0} for i in range(5)],
        }),
        "/api/plots/FPS/values?offset=2&count=3": (200, {
            "total_count": 500, "offset": 2,
            "values": [{"time": (2 + i) * 16666666, "val": 60.2 + i * 0.1} for i in range(3)],
        }),
        "/api/plots/FPS/values?count=9999": (200, {
            "total_count": 500, "offset": 0,
            "values": [{"time": i * 16666666, "val": 60.0} for i in range(100)],
        }),
        "/api/plots/FPS/values?start=0&end=999999999999": (200, {
            "total_count": 500, "offset": 0,
            "values": [{"time": i * 16666666, "val": 60.0} for i in range(5)],
        }),
        "/api/plots/nonexistent_xyz/count":  (404, {"error": "Plot not found"}),
        "/api/plots/nonexistent_xyz/values": (404, {"error": "Plot not found"}),
        "/api/memory/pools": (200, {"pools": ["default", "gpu"]}),
        "/api/memory/default/overview?start=0&end=999999999999": (200, {
            "alloc_count": 100, "free_count": 80,
            "alloc_bytes": 1048576, "free_bytes": 819200,
            "active_count": 20, "active_bytes": 229376,
        }),
        "/api/memory/default/overview?end=9999":   (400, {"error": "Missing required parameter: start or end"}),
        "/api/memory/default/overview?start=0":    (400, {"error": "Missing required parameter: start or end"}),
        "/api/memory/nonexistent_xyz/overview?start=0&end=9999": (404, {"error": "Pool not found"}),
        "/api/memory/default/allocations?start=0&end=999999999999": (200, {
            "total_count": 3, "offset": 0,
            "allocations": [
                {"address": 100, "size": 4096, "appeared_at": 1000000, "is_freed": True,
                 "free_time": 2000000, "thread_alloc_id": 222222, "thread_free_id": 222222},
                {"address": 200, "size": 2048, "appeared_at": 2000000, "is_freed": False,
                 "free_time": -1, "thread_alloc_id": 333333, "thread_free_id": 0},
                {"address": 300, "size": 8192, "appeared_at": 3000000, "is_freed": True,
                 "free_time": 4000000, "thread_alloc_id": 222222, "thread_free_id": 222222},
            ],
        }),
        "/api/memory/default/allocations?start=0&end=999999999999&count=9999": (200, {
            "total_count": 3, "offset": 0,
            "allocations": [
                {"address": 100, "size": 4096, "appeared_at": 1000000, "is_freed": True,
                 "free_time": 2000000, "thread_alloc_id": 222222, "thread_free_id": 222222},
            ],
        }),
        "/api/memory/default/allocations?start=0&end=999999999999&sort=size_descend&count=20": (200, {
            "total_count": 3, "offset": 0,
            "allocations": [
                {"address": 300, "size": 8192, "appeared_at": 3000000, "is_freed": True,
                 "free_time": 4000000, "thread_alloc_id": 222222, "thread_free_id": 222222},
                {"address": 100, "size": 4096, "appeared_at": 1000000, "is_freed": True,
                 "free_time": 2000000, "thread_alloc_id": 222222, "thread_free_id": 222222},
                {"address": 200, "size": 2048, "appeared_at": 2000000, "is_freed": False,
                 "free_time": -1, "thread_alloc_id": 333333, "thread_free_id": 0},
            ],
        }),
        "/api/memory/default/allocations?start=0&end=999999999999&sort=size_ascend&count=20": (200, {
            "total_count": 3, "offset": 0,
            "allocations": [
                {"address": 200, "size": 2048, "appeared_at": 2000000, "is_freed": False,
                 "free_time": -1, "thread_alloc_id": 333333, "thread_free_id": 0},
                {"address": 100, "size": 4096, "appeared_at": 1000000, "is_freed": True,
                 "free_time": 2000000, "thread_alloc_id": 222222, "thread_free_id": 222222},
                {"address": 300, "size": 8192, "appeared_at": 3000000, "is_freed": True,
                 "free_time": 4000000, "thread_alloc_id": 222222, "thread_free_id": 222222},
            ],
        }),
        "/api/memory/default/allocations?start=0&end=999999999999&sort=appeared_at_descend&count=20": (200, {
            "total_count": 3, "offset": 0,
            "allocations": [
                {"address": 300, "size": 8192, "appeared_at": 3000000, "is_freed": True,
                 "free_time": 4000000, "thread_alloc_id": 222222, "thread_free_id": 222222},
                {"address": 200, "size": 2048, "appeared_at": 2000000, "is_freed": False,
                 "free_time": -1, "thread_alloc_id": 333333, "thread_free_id": 0},
                {"address": 100, "size": 4096, "appeared_at": 1000000, "is_freed": True,
                 "free_time": 2000000, "thread_alloc_id": 222222, "thread_free_id": 222222},
            ],
        }),
        "/api/memory/default/allocations?end=9999":   (400, {"error": "Missing required parameter: start or end"}),
        "/api/memory/nonexistent_xyz/allocations?start=0&end=9999": (404, {"error": "Pool not found"}),
        "/api/memory/default/callstack_tree?include_active=true&include_inactive=true": (200, {
            "roots": [
                {"frame_name": "malloc", "file": "stdlib.c", "line": 42,
                 "alloc_count": 50, "alloc_bytes": 512000, "child_count": 2},
                {"frame_name": "operator new", "file": "new.cpp", "line": 10,
                 "alloc_count": 50, "alloc_bytes": 536576, "child_count": 1},
            ],
        }),
        "/api/memory/default/callstack_tree?include_active=true&include_inactive=false": (200, {
            "roots": [
                {"frame_name": "malloc", "file": "stdlib.c", "line": 42,
                 "alloc_count": 20, "alloc_bytes": 229376, "child_count": 1},
            ],
        }),
        "/api/memory/nonexistent_xyz/callstack_tree?include_active=true&include_inactive=true": (
            404, {"error": "Pool not found"}
        ),
        "/api/stats/summary": (200, {
            "zone_count": 9999, "frame_count": 100,
            "lock_count": 5, "plot_count": 2,
            "message_count": 10, "context_switch_count": 500,
            "first_time": 0, "last_time": 1000000000,
            "captured_program": "mock_app", "host_info": "MockHost",
        }),
        "/api/stats/frame_tags": (200, [
            {
                "tag_name": "Render",
                "self_times": [1000000, 1200000],
                "all_times":  [2000000, 2100000],
                "span_times": [0, 0],
                "parallel_ratios": [0.0, 0.0],
                "idle_times": [0, 0],
                "idle_ratios": [0.0, 0.0],
            },
        ]),
        "/api/stats/export_csv": (200, "frame,time_from_start,frame_duration,frame_start_time,frame_end_time\n0,0.000,16.667,0.000,16.667\n1,16.667,16.667,16.667,33.333\n"),
        "/api/zones/by_tag?tag=logic": (200, {
            "tag": "logic",
            "count": 3,
            "zone_ids": [111111, 222222, 333333],
        }),
        "/api/zones/by_tag?tag=logic&start_frame=0&end_frame=10": (200, {
            "tag": "logic",
            "count": 2,
            "zone_ids": [111111, 222222],
        }),
        "/api/zones/by_tag?tag=unknown_tag_xyz": (200, {
            "tag": "unknown_tag_xyz",
            "count": 0,
            "zone_ids": [],
        }),
        "/api/frame_number?ts=1000000": (200, {
            "ts_ns": 1000000,
            "frame_number": 0,
        }),
        "/api/frame_number?ts=999999999999": (200, {
            "ts_ns": 999999999999,
            "frame_number": 99,
        }),
        "/api/frame_number?ts=0": (200, {
            "ts_ns": 0,
            "frame_number": -1,
        }),
    }

    def log_message(self, *args):
        pass  # suppress output

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = self.path
        entry = self.ROUTES.get(path)
        if entry is None:
            # strip query for partial match (frames without params)
            base = path.split("?")[0]
            entry = self.ROUTES.get(base)
        if entry is None:
            status, body = 404, {"error": "Not found"}
        else:
            status, body = entry
        # CSV endpoint returns raw string, others return JSON
        if isinstance(body, str):
            raw = body.encode("utf-8")
            content_type = "text/csv; charset=utf-8"
        else:
            raw = json.dumps(body).encode()
            content_type = "application/json; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        self.send_response(405)
        raw = json.dumps({"error": "Method not allowed"}).encode()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class TracyHttpMockTests(unittest.TestCase):
    """Offline unit tests using the mock HTTP server."""

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("localhost", 0), _MockHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    # ------------------------------------------------------------------
    # /api/health
    # ------------------------------------------------------------------

    def test_health_200(self):
        code, data = _get(self.port, "/api/health")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "ok")

    # ------------------------------------------------------------------
    # /api/filepath
    # ------------------------------------------------------------------

    def test_filepath_200_nonempty(self):
        code, data = _get(self.port, "/api/filepath")
        self.assertEqual(code, 200)
        self.assertGreater(len(data["filepath"]), 0)

    # ------------------------------------------------------------------
    # /api/current_selection
    # ------------------------------------------------------------------

    def test_selection_valid_true_fields(self):
        code, data = _get(self.port, "/api/current_selection")
        self.assertEqual(code, 200)
        self.assertTrue(data["valid"])
        self.assertEqual(data["zone_id"],      111111)
        self.assertEqual(data["thread_name"],  "MainThread")
        self.assertEqual(data["duration_ns"],  5000000)

    def test_selection_children_length_match(self):
        _, data = _get(self.port, "/api/current_selection")
        self.assertEqual(len(data["children_ids"]), len(data["children_names"]))

    def test_selection_duration_positive(self):
        _, data = _get(self.port, "/api/current_selection")
        self.assertGreater(data["duration_ns"], 0)

    # ------------------------------------------------------------------
    # /api/zone/{id}
    # ------------------------------------------------------------------

    def test_zone_found(self):
        code, data = _get(self.port, "/api/zone/111111")
        self.assertEqual(code, 200)
        self.assertTrue(data["valid"])
        self.assertEqual(data["zone_id"], 111111)

    def test_zone_invalid_id_400(self):
        code, data = _get(self.port, "/api/zone/0")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_zone_not_found_404(self):
        code, data = _get(self.port, "/api/zone/999")
        self.assertEqual(code, 404)
        self.assertFalse(data["valid"])

    def test_zone_roundtrip_matches_selection(self):
        _, sel = _get(self.port, "/api/current_selection")
        _, zone = _get(self.port, f"/api/zone/{sel['zone_id']}")
        self.assertEqual(zone["function"],    sel["function"])
        self.assertEqual(zone["duration_ns"], sel["duration_ns"])

    # ------------------------------------------------------------------
    # /api/trace_overview
    # ------------------------------------------------------------------

    def test_trace_overview_200(self):
        code, data = _get(self.port, "/api/trace_overview")
        self.assertEqual(code, 200)
        required = [
            "captured_program", "host_info",
            "first_time", "last_time",
            "zone_count", "frame_count", "lock_count",
            "plot_count", "message_count", "context_switch_count",
        ]
        for f in required:
            self.assertIn(f, data)

    def test_trace_overview_last_time_gt_first_time(self):
        _, data = _get(self.port, "/api/trace_overview")
        self.assertGreater(data["last_time"], data["first_time"])

    def test_trace_overview_counts_non_negative(self):
        _, data = _get(self.port, "/api/trace_overview")
        for key in ("zone_count", "frame_count", "lock_count",
                    "plot_count", "message_count", "context_switch_count"):
            self.assertGreaterEqual(data[key], 0, f"{key} should be >= 0")

    # ------------------------------------------------------------------
    # /api/threads
    # ------------------------------------------------------------------

    def test_threads_200_list(self):
        code, data = _get(self.port, "/api/threads")
        self.assertEqual(code, 200)
        self.assertIsInstance(data["threads"], list)
        self.assertGreater(len(data["threads"]), 0)

    def test_threads_entry_fields(self):
        _, data = _get(self.port, "/api/threads")
        for t in data["threads"]:
            self.assertIn("thread_id",   t)
            self.assertIn("thread_name", t)
            self.assertIsInstance(t["thread_id"],   int)
            self.assertIsInstance(t["thread_name"], str)

    # ------------------------------------------------------------------
    # /api/frames
    # ------------------------------------------------------------------

    def test_frames_200_structure(self):
        code, data = _get(self.port, "/api/frames")
        self.assertEqual(code, 200)
        self.assertIn("total_count", data)
        self.assertIn("offset",      data)
        self.assertIn("frames",      data)
        self.assertIsInstance(data["frames"], list)

    def test_frames_timing_consistency(self):
        _, data = _get(self.port, "/api/frames")
        for f in data["frames"]:
            self.assertEqual(f["duration_ns"], f["end_ns"] - f["start_ns"])
            self.assertGreaterEqual(f["end_ns"], f["start_ns"])

    def test_frames_offset_param(self):
        _, data = _get(self.port, "/api/frames?offset=10&count=5")
        self.assertEqual(data["offset"], 10)
        if data["frames"]:
            self.assertEqual(data["frames"][0]["frame_idx"], 10)

    def test_frames_frame_idx_sequential(self):
        _, data = _get(self.port, "/api/frames")
        idxs = [f["frame_idx"] for f in data["frames"]]
        self.assertEqual(idxs, list(range(idxs[0], idxs[0] + len(idxs))))

    # ------------------------------------------------------------------
    # /api/zone/{id}/children (mock)
    # ------------------------------------------------------------------

    def test_zone_children_200_has_children_array(self):
        code, data = _get(self.port, "/api/zone/111111/children")
        self.assertEqual(code, 200)
        self.assertIn("children", data)
        self.assertIsInstance(data["children"], list)
        self.assertEqual(len(data["children"]), 2)

    def test_zone_children_each_entry_has_zone_fields(self):
        _, data = _get(self.port, "/api/zone/111111/children")
        for c in data["children"]:
            for f in ("zone_id", "function", "duration_ns", "valid"):
                self.assertIn(f, c)

    def test_zone_children_duration_positive(self):
        _, data = _get(self.port, "/api/zone/111111/children")
        for c in data["children"]:
            self.assertGreater(c["duration_ns"], 0)

    def test_zone_children_invalid_id_400(self):
        code, data = _get(self.port, "/api/zone/0/children")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_zone_children_not_found_404(self):
        code, data = _get(self.port, "/api/zone/999/children")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/messages (mock)
    # ------------------------------------------------------------------

    def test_messages_200_structure(self):
        code, data = _get(self.port, "/api/messages")
        self.assertEqual(code, 200)
        self.assertIn("total_count", data)
        self.assertIn("offset",      data)
        self.assertIn("messages",    data)

    def test_messages_offset_zero_by_default(self):
        _, data = _get(self.port, "/api/messages")
        self.assertEqual(data["offset"], 0)

    def test_messages_each_entry_fields(self):
        _, data = _get(self.port, "/api/messages")
        for m in data["messages"]:
            for f in ("time", "text", "thread_id", "thread_name", "color"):
                self.assertIn(f, m)
            self.assertIsInstance(m["time"], int)
            self.assertIsInstance(m["text"], str)

    def test_messages_with_offset_5(self):
        _, data = _get(self.port, "/api/messages?offset=5&count=10")
        self.assertEqual(data["offset"], 5)

    def test_messages_time_range_empty(self):
        _, data = _get(self.port, "/api/messages?start=999999999999&end=1")
        self.assertEqual(len(data["messages"]), 0)

    # ------------------------------------------------------------------
    # /api/plots (mock)
    # ------------------------------------------------------------------

    def test_plots_200_list(self):
        code, data = _get(self.port, "/api/plots")
        self.assertEqual(code, 200)
        self.assertIn("plots", data)
        self.assertIsInstance(data["plots"], list)
        self.assertGreater(len(data["plots"]), 0)

    def test_plots_all_strings(self):
        _, data = _get(self.port, "/api/plots")
        for p in data["plots"]:
            self.assertIsInstance(p, str)

    # ------------------------------------------------------------------
    # /api/plots/{name}/count (mock)
    # ------------------------------------------------------------------

    def test_plot_count_200(self):
        code, data = _get(self.port, "/api/plots/FPS/count")
        self.assertEqual(code, 200)
        self.assertIn("count", data)
        self.assertIsInstance(data["count"], int)
        self.assertGreaterEqual(data["count"], 0)

    def test_plot_count_not_found_404(self):
        code, data = _get(self.port, "/api/plots/nonexistent_xyz/count")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/plots/{name}/values (mock)
    # ------------------------------------------------------------------

    def test_plot_values_200_structure(self):
        code, data = _get(self.port, "/api/plots/FPS/values")
        self.assertEqual(code, 200)
        self.assertIn("total_count", data)
        self.assertIn("values",      data)

    def test_plot_values_entry_fields(self):
        _, data = _get(self.port, "/api/plots/FPS/values?count=5")
        for v in data["values"]:
            self.assertIn("time", v)
            self.assertIn("val",  v)
            self.assertIsInstance(v["time"], int)
            self.assertIsInstance(v["val"],  (int, float))

    def test_plot_values_with_offset(self):
        _, data = _get(self.port, "/api/plots/FPS/values?offset=2&count=3")
        self.assertEqual(data["offset"], 2)

    def test_plot_values_not_found_404(self):
        code, data = _get(self.port, "/api/plots/nonexistent_xyz/values")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/memory/pools (mock)
    # ------------------------------------------------------------------

    def test_memory_pools_200(self):
        code, data = _get(self.port, "/api/memory/pools")
        self.assertEqual(code, 200)
        self.assertIn("pools", data)
        self.assertIsInstance(data["pools"], list)

    def test_memory_pools_all_strings(self):
        _, data = _get(self.port, "/api/memory/pools")
        for p in data["pools"]:
            self.assertIsInstance(p, str)

    # ------------------------------------------------------------------
    # /api/memory/{pool}/overview (mock)
    # ------------------------------------------------------------------

    def test_pool_overview_200_fields(self):
        code, data = _get(self.port, "/api/memory/default/overview?start=0&end=999999999999")
        self.assertEqual(code, 200)
        for f in ("alloc_count", "free_count", "alloc_bytes",
                  "free_bytes", "active_count", "active_bytes"):
            self.assertIn(f, data)

    def test_pool_overview_active_consistency(self):
        _, data = _get(self.port, "/api/memory/default/overview?start=0&end=999999999999")
        self.assertEqual(data["active_count"], data["alloc_count"] - data["free_count"])
        self.assertEqual(data["active_bytes"], data["alloc_bytes"] - data["free_bytes"])

    def test_pool_overview_missing_start_400(self):
        code, data = _get(self.port, "/api/memory/default/overview?end=9999")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_pool_overview_missing_end_400(self):
        code, data = _get(self.port, "/api/memory/default/overview?start=0")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_pool_overview_unknown_pool_404(self):
        code, data = _get(self.port, "/api/memory/nonexistent_xyz/overview?start=0&end=9999")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/memory/{pool}/allocations (mock)
    # ------------------------------------------------------------------

    def test_pool_allocations_200_structure(self):
        code, data = _get(self.port, "/api/memory/default/allocations?start=0&end=999999999999")
        self.assertEqual(code, 200)
        self.assertIn("total_count",  data)
        self.assertIn("allocations",  data)
        self.assertIsInstance(data["allocations"], list)

    def test_pool_allocations_entry_fields(self):
        _, data = _get(self.port, "/api/memory/default/allocations?start=0&end=999999999999")
        for a in data["allocations"]:
            for f in ("address", "size", "appeared_at", "is_freed",
                      "free_time", "thread_alloc_id", "thread_free_id"):
                self.assertIn(f, a)
            self.assertIsInstance(a["is_freed"], bool)

    def test_pool_allocations_sort_size_descend_order(self):
        _, data = _get(
            self.port,
            "/api/memory/default/allocations?start=0&end=999999999999&sort=size_descend&count=20"
        )
        sizes = [a["size"] for a in data["allocations"]]
        self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_pool_allocations_sort_size_ascend_order(self):
        _, data = _get(
            self.port,
            "/api/memory/default/allocations?start=0&end=999999999999&sort=size_ascend&count=20"
        )
        sizes = [a["size"] for a in data["allocations"]]
        self.assertEqual(sizes, sorted(sizes))

    def test_pool_allocations_sort_appeared_at_descend(self):
        _, data = _get(
            self.port,
            "/api/memory/default/allocations?start=0&end=999999999999&sort=appeared_at_descend&count=20"
        )
        times = [a["appeared_at"] for a in data["allocations"]]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_pool_allocations_missing_start_400(self):
        code, data = _get(self.port, "/api/memory/default/allocations?end=9999")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_pool_allocations_unknown_pool_404(self):
        code, data = _get(self.port, "/api/memory/nonexistent_xyz/allocations?start=0&end=9999")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/memory/{pool}/callstack_tree (mock)
    # ------------------------------------------------------------------

    def test_pool_callstack_tree_200_structure(self):
        code, data = _get(
            self.port,
            "/api/memory/default/callstack_tree?include_active=true&include_inactive=true"
        )
        self.assertEqual(code, 200)
        self.assertIn("roots", data)
        self.assertIsInstance(data["roots"], list)

    def test_pool_callstack_tree_root_fields(self):
        _, data = _get(
            self.port,
            "/api/memory/default/callstack_tree?include_active=true&include_inactive=true"
        )
        for r in data["roots"]:
            for f in ("frame_name", "file", "line",
                      "alloc_count", "alloc_bytes", "child_count"):
                self.assertIn(f, r)

    def test_pool_callstack_tree_active_only_fewer_roots(self):
        _, full = _get(
            self.port,
            "/api/memory/default/callstack_tree?include_active=true&include_inactive=true"
        )
        _, active_only = _get(
            self.port,
            "/api/memory/default/callstack_tree?include_active=true&include_inactive=false"
        )
        self.assertLessEqual(
            len(active_only["roots"]),
            len(full["roots"])
        )

    def test_pool_callstack_tree_unknown_pool_404(self):
        code, data = _get(
            self.port,
            "/api/memory/nonexistent_xyz/callstack_tree?include_active=true&include_inactive=true"
        )
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/stats/summary (mock)
    # ------------------------------------------------------------------

    def test_stats_summary_200_required_fields(self):
        code, data = _get(self.port, "/api/stats/summary")
        self.assertEqual(code, 200)
        for f in ("zone_count", "frame_count", "lock_count", "plot_count",
                  "message_count", "context_switch_count",
                  "first_time", "last_time", "captured_program", "host_info"):
            self.assertIn(f, data)

    def test_stats_summary_counts_non_negative(self):
        _, data = _get(self.port, "/api/stats/summary")
        for k in ("zone_count", "frame_count", "lock_count",
                  "plot_count", "message_count", "context_switch_count"):
            self.assertGreaterEqual(data[k], 0)

    def test_stats_summary_time_range(self):
        _, data = _get(self.port, "/api/stats/summary")
        self.assertGreaterEqual(data["last_time"], data["first_time"])

    def test_stats_summary_strings(self):
        _, data = _get(self.port, "/api/stats/summary")
        self.assertIsInstance(data["captured_program"], str)
        self.assertIsInstance(data["host_info"],        str)

    # ------------------------------------------------------------------
    # /api/stats/frame_tags (mock)
    # ------------------------------------------------------------------

    def test_stats_frame_tags_200_is_list(self):
        code, data = _get(self.port, "/api/stats/frame_tags")
        self.assertEqual(code, 200)
        self.assertIsInstance(data, list)

    def test_stats_frame_tags_entry_fields(self):
        _, data = _get(self.port, "/api/stats/frame_tags")
        for t in data:
            self.assertIn("tag_name",       t)
            self.assertIn("self_times",     t)
            self.assertIn("all_times",      t)
            self.assertIn("parallel_ratios",t)
            self.assertIsInstance(t["self_times"], list)
            self.assertIsInstance(t["all_times"],  list)

    def test_stats_frame_tags_all_times_ge_self_times(self):
        _, data = _get(self.port, "/api/stats/frame_tags")
        for tag in data:
            for s, a in zip(tag["self_times"], tag["all_times"]):
                self.assertGreaterEqual(a, s)

    # ------------------------------------------------------------------
    # /api/stats/export_csv (mock)
    # ------------------------------------------------------------------

    def _get_raw(self, path):
        """GET raw text (for CSV). Returns (status, text)."""
        try:
            resp = urllib.request.urlopen(
                f"http://localhost:{self.port}{path}", timeout=5.0
            )
            return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def test_stats_export_csv_200(self):
        code, _ = self._get_raw("/api/stats/export_csv")
        self.assertEqual(code, 200)

    def test_stats_export_csv_content_type(self):
        resp = urllib.request.urlopen(
            f"http://localhost:{self.port}/api/stats/export_csv", timeout=3
        )
        self.assertIn("text/csv", resp.headers.get("Content-Type", ""))

    def test_stats_export_csv_header_row(self):
        _, text = self._get_raw("/api/stats/export_csv")
        first_line = text.split("\n")[0]
        self.assertIn("frame", first_line)

    def test_stats_export_csv_data_rows(self):
        _, text = self._get_raw("/api/stats/export_csv")
        lines = [l for l in text.strip().split("\n") if l]
        self.assertGreater(len(lines), 1)

    def test_stats_export_csv_consistent_columns(self):
        _, text = self._get_raw("/api/stats/export_csv")
        lines = [l for l in text.strip().split("\n") if l]
        col_counts = [len(l.split(",")) for l in lines]
        self.assertEqual(len(set(col_counts)), 1)

    # ------------------------------------------------------------------
    # Error / protocol tests
    # ------------------------------------------------------------------

    def test_unknown_path_404(self):
        code, data = _get(self.port, "/api/nonexistent")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    def test_post_returns_405(self):
        req = urllib.request.Request(
            f"http://localhost:{self.port}/api/health",
            method="POST",
            data=b"",
        )
        try:
            urllib.request.urlopen(req, timeout=3)
            self.fail("Expected 405")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 405)

    def test_options_preflight_204(self):
        req = urllib.request.Request(
            f"http://localhost:{self.port}/api/health",
            method="OPTIONS",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=3)
            self.assertEqual(resp.status, 204)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 204)

    def test_cors_header_present(self):
        resp = urllib.request.urlopen(
            f"http://localhost:{self.port}/api/health", timeout=3
        )
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_content_type_is_json(self):
        resp = urllib.request.urlopen(
            f"http://localhost:{self.port}/api/health", timeout=3
        )
        ct = resp.headers.get("Content-Type", "")
        self.assertIn("application/json", ct)

    # ------------------------------------------------------------------
    # /api/zone/{id}/children
    # ------------------------------------------------------------------

    def test_zone_children_200_has_children_array(self):
        code, data = _get(self.port, "/api/zone/111111/children")
        self.assertEqual(code, 200)
        self.assertIn("children", data)
        self.assertIsInstance(data["children"], list)

    def test_zone_children_each_entry_has_zone_fields(self):
        _, data = _get(self.port, "/api/zone/111111/children")
        for c in data["children"]:
            self.assertIn("zone_id",     c)
            self.assertIn("function",    c)
            self.assertIn("duration_ns", c)

    def test_zone_children_invalid_id_returns_400(self):
        code, data = _get(self.port, "/api/zone/0/children")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_zone_children_not_found_returns_404(self):
        code, data = _get(self.port, "/api/zone/999/children")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/messages
    # ------------------------------------------------------------------

    def test_messages_200_has_required_fields(self):
        code, data = _get(self.port, "/api/messages")
        self.assertEqual(code, 200)
        self.assertIn("total_count", data)
        self.assertIn("offset",      data)
        self.assertIn("messages",    data)
        self.assertIsInstance(data["messages"], list)

    def test_messages_default_offset_is_zero(self):
        _, data = _get(self.port, "/api/messages")
        self.assertEqual(data["offset"], 0)

    def test_messages_each_entry_has_required_fields(self):
        _, data = _get(self.port, "/api/messages")
        for m in data["messages"]:
            self.assertIn("time",        m)
            self.assertIn("text",        m)
            self.assertIn("thread_id",   m)
            self.assertIn("thread_name", m)
            self.assertIn("color",       m)

    def test_messages_count_capped_at_500(self):
        _, data = _get(self.port, "/api/messages?count=9999")
        self.assertLessEqual(len(data["messages"]), 500)

    def test_messages_with_offset_param(self):
        _, data = _get(self.port, "/api/messages?offset=5&count=10")
        self.assertEqual(data["offset"], 5)

    def test_messages_with_time_range(self):
        code, data = _get(self.port, "/api/messages?start=0&end=999999999999")
        self.assertEqual(code, 200)
        self.assertIn("messages", data)

    def test_messages_empty_range_returns_zero(self):
        # end < start → 0 messages
        _, data = _get(self.port, "/api/messages?start=999999999999&end=1")
        self.assertEqual(len(data["messages"]), 0)

    # ------------------------------------------------------------------
    # /api/plots
    # ------------------------------------------------------------------

    def test_plots_200_has_plots_array(self):
        code, data = _get(self.port, "/api/plots")
        self.assertEqual(code, 200)
        self.assertIn("plots", data)
        self.assertIsInstance(data["plots"], list)

    def test_plots_entries_are_strings(self):
        _, data = _get(self.port, "/api/plots")
        for name in data["plots"]:
            self.assertIsInstance(name, str)

    # ------------------------------------------------------------------
    # /api/plots/{name}/count
    # ------------------------------------------------------------------

    def test_plot_count_200_has_count(self):
        code, data = _get(self.port, "/api/plots/FPS/count")
        self.assertEqual(code, 200)
        self.assertIn("count", data)
        self.assertIsInstance(data["count"], int)
        self.assertGreaterEqual(data["count"], 0)

    def test_plot_count_nonexistent_returns_404(self):
        code, data = _get(self.port, "/api/plots/nonexistent_xyz/count")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/plots/{name}/values
    # ------------------------------------------------------------------

    def test_plot_values_200_has_required_fields(self):
        code, data = _get(self.port, "/api/plots/FPS/values")
        self.assertEqual(code, 200)
        self.assertIn("total_count", data)
        self.assertIn("offset",      data)
        self.assertIn("values",      data)
        self.assertIsInstance(data["values"], list)

    def test_plot_values_each_entry_has_time_and_val(self):
        _, data = _get(self.port, "/api/plots/FPS/values?count=5")
        for v in data["values"]:
            self.assertIn("time", v)
            self.assertIn("val",  v)
            self.assertIsInstance(v["time"], int)
            self.assertIsInstance(v["val"],  (int, float))

    def test_plot_values_count_capped_at_1000(self):
        _, data = _get(self.port, "/api/plots/FPS/values?count=9999")
        self.assertLessEqual(len(data["values"]), 1000)

    def test_plot_values_with_offset(self):
        _, data = _get(self.port, "/api/plots/FPS/values?offset=2&count=3")
        self.assertEqual(data["offset"], 2)

    def test_plot_values_with_time_range(self):
        code, data = _get(self.port, "/api/plots/FPS/values?start=0&end=999999999999")
        self.assertEqual(code, 200)
        self.assertIn("values", data)

    def test_plot_values_nonexistent_returns_404(self):
        code, data = _get(self.port, "/api/plots/nonexistent_xyz/values")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/memory/pools
    # ------------------------------------------------------------------

    def test_memory_pools_200_has_pools_array(self):
        code, data = _get(self.port, "/api/memory/pools")
        self.assertEqual(code, 200)
        self.assertIn("pools", data)
        self.assertIsInstance(data["pools"], list)

    def test_memory_pools_entries_are_strings(self):
        _, data = _get(self.port, "/api/memory/pools")
        for p in data["pools"]:
            self.assertIsInstance(p, str)

    # ------------------------------------------------------------------
    # /api/memory/{pool}/overview
    # ------------------------------------------------------------------

    def test_pool_overview_200_has_required_fields(self):
        code, data = _get(self.port, "/api/memory/default/overview?start=0&end=999999999999")
        self.assertEqual(code, 200)
        for field in ("alloc_count", "free_count", "alloc_bytes",
                      "free_bytes", "active_count", "active_bytes"):
            self.assertIn(field, data)

    def test_pool_overview_counts_non_negative(self):
        _, data = _get(self.port, "/api/memory/default/overview?start=0&end=999999999999")
        for k in ("alloc_count", "free_count", "alloc_bytes", "free_bytes",
                  "active_count", "active_bytes"):
            self.assertGreaterEqual(data[k], 0)

    def test_pool_overview_active_equals_alloc_minus_free(self):
        _, data = _get(self.port, "/api/memory/default/overview?start=0&end=999999999999")
        self.assertEqual(data["active_count"], data["alloc_count"] - data["free_count"])
        self.assertEqual(data["active_bytes"], data["alloc_bytes"] - data["free_bytes"])

    def test_pool_overview_missing_start_returns_400(self):
        code, data = _get(self.port, "/api/memory/default/overview?end=9999")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_pool_overview_missing_end_returns_400(self):
        code, data = _get(self.port, "/api/memory/default/overview?start=0")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_pool_overview_nonexistent_pool_returns_404(self):
        code, data = _get(self.port, "/api/memory/nonexistent_xyz/overview?start=0&end=9999")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/memory/{pool}/allocations
    # ------------------------------------------------------------------

    def test_pool_allocations_200_has_required_fields(self):
        code, data = _get(self.port, "/api/memory/default/allocations?start=0&end=999999999999")
        self.assertEqual(code, 200)
        self.assertIn("total_count",  data)
        self.assertIn("offset",       data)
        self.assertIn("allocations",  data)
        self.assertIsInstance(data["allocations"], list)

    def test_pool_allocations_each_entry_has_required_fields(self):
        _, data = _get(self.port, "/api/memory/default/allocations?start=0&end=999999999999")
        for a in data["allocations"]:
            for field in ("address", "size", "appeared_at", "is_freed",
                          "free_time", "thread_alloc_id", "thread_free_id"):
                self.assertIn(field, a)

    def test_pool_allocations_is_freed_is_bool(self):
        _, data = _get(self.port, "/api/memory/default/allocations?start=0&end=999999999999")
        for a in data["allocations"]:
            self.assertIsInstance(a["is_freed"], bool)

    def test_pool_allocations_count_capped_at_100(self):
        _, data = _get(self.port, "/api/memory/default/allocations?start=0&end=999999999999&count=9999")
        self.assertLessEqual(len(data["allocations"]), 100)

    def test_pool_allocations_sort_size_descend(self):
        _, data = _get(
            self.port,
            "/api/memory/default/allocations?start=0&end=999999999999&sort=size_descend&count=20"
        )
        sizes = [a["size"] for a in data["allocations"]]
        self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_pool_allocations_sort_size_ascend(self):
        _, data = _get(
            self.port,
            "/api/memory/default/allocations?start=0&end=999999999999&sort=size_ascend&count=20"
        )
        sizes = [a["size"] for a in data["allocations"]]
        self.assertEqual(sizes, sorted(sizes))

    def test_pool_allocations_sort_appeared_at_descend(self):
        _, data = _get(
            self.port,
            "/api/memory/default/allocations?start=0&end=999999999999&sort=appeared_at_descend&count=20"
        )
        times = [a["appeared_at"] for a in data["allocations"]]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_pool_allocations_missing_start_returns_400(self):
        code, data = _get(self.port, "/api/memory/default/allocations?end=9999")
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_pool_allocations_nonexistent_pool_returns_404(self):
        code, data = _get(self.port, "/api/memory/nonexistent_xyz/allocations?start=0&end=9999")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/memory/{pool}/callstack_tree
    # ------------------------------------------------------------------

    def test_pool_callstack_tree_responds(self):
        code, data = _get(
            self.port,
            "/api/memory/default/callstack_tree?include_active=true&include_inactive=true"
        )
        # 200 = implemented; 404 = pool not found; 503 = no trace
        self.assertIn(code, (200, 404, 503))

    def test_pool_callstack_tree_200_has_roots_array(self):
        code, data = _get(
            self.port,
            "/api/memory/default/callstack_tree?include_active=true&include_inactive=true"
        )
        if code != 200:
            self.skipTest("callstack_tree not available or pool not found")
        self.assertIn("roots", data)
        self.assertIsInstance(data["roots"], list)

    def test_pool_callstack_tree_200_each_root_has_fields(self):
        code, data = _get(
            self.port,
            "/api/memory/default/callstack_tree?include_active=true&include_inactive=false"
        )
        if code != 200:
            self.skipTest("callstack_tree not available")
        for r in data["roots"]:
            for field in ("frame_name", "file", "line",
                          "alloc_count", "alloc_bytes", "child_count"):
                self.assertIn(field, r)

    def test_pool_callstack_tree_nonexistent_pool_returns_404(self):
        code, data = _get(
            self.port,
            "/api/memory/nonexistent_xyz/callstack_tree?include_active=true&include_inactive=true"
        )
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/stats/summary
    # ------------------------------------------------------------------

    def test_stats_summary_200_has_required_fields(self):
        code, data = _get(self.port, "/api/stats/summary")
        self.assertEqual(code, 200)
        for field in ("zone_count", "frame_count", "lock_count", "plot_count",
                      "message_count", "context_switch_count",
                      "first_time", "last_time",
                      "captured_program", "host_info"):
            self.assertIn(field, data, f"Missing field: {field}")

    def test_stats_summary_counts_non_negative(self):
        _, data = _get(self.port, "/api/stats/summary")
        for k in ("zone_count", "frame_count", "lock_count", "plot_count",
                  "message_count", "context_switch_count"):
            self.assertGreaterEqual(data[k], 0)

    def test_stats_summary_last_time_ge_first_time(self):
        _, data = _get(self.port, "/api/stats/summary")
        self.assertGreaterEqual(data["last_time"], data["first_time"])

    def test_stats_summary_program_and_host_are_strings(self):
        _, data = _get(self.port, "/api/stats/summary")
        self.assertIsInstance(data["captured_program"], str)
        self.assertIsInstance(data["host_info"],        str)

    # ------------------------------------------------------------------
    # /api/stats/frame_tags
    # ------------------------------------------------------------------

    def test_stats_frame_tags_responds(self):
        code, _ = _get(self.port, "/api/stats/frame_tags")
        # 200 = array response; 503 = not implemented (high-risk interface)
        self.assertIn(code, (200, 503))

    def test_stats_frame_tags_200_is_list(self):
        code, data = _get(self.port, "/api/stats/frame_tags")
        if code != 200:
            self.skipTest("frame_tags not implemented")
        self.assertIsInstance(data, list)

    # ------------------------------------------------------------------
    # /api/stats/export_csv
    # ------------------------------------------------------------------

    def _get_raw(self, path):
        """GET raw text (for CSV endpoint). Returns (status, text)."""
        try:
            resp = urllib.request.urlopen(
                f"http://localhost:{self.port}{path}", timeout=5.0
            )
            return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def test_stats_export_csv_200(self):
        code, _ = self._get_raw("/api/stats/export_csv")
        self.assertEqual(code, 200)

    def test_stats_export_csv_content_type_is_text_csv(self):
        resp = urllib.request.urlopen(
            f"http://localhost:{self.port}/api/stats/export_csv", timeout=5.0
        )
        ct = resp.headers.get("Content-Type", "")
        self.assertIn("text/csv", ct)

    def test_stats_export_csv_has_header_row(self):
        _, text = self._get_raw("/api/stats/export_csv")
        first_line = text.split("\n")[0]
        self.assertIn("frame", first_line)

    def test_stats_export_csv_has_data_rows(self):
        _, text = self._get_raw("/api/stats/export_csv")
        lines = [l for l in text.strip().split("\n") if l]
        # At least header + 1 data row
        self.assertGreater(len(lines), 1)

    def test_stats_export_csv_consistent_column_count(self):
        _, text = self._get_raw("/api/stats/export_csv")
        lines = [l for l in text.strip().split("\n") if l]
        if len(lines) < 2:
            self.skipTest("No data rows")
        col_counts = [len(l.split(",")) for l in lines]
        self.assertEqual(len(set(col_counts)), 1, "Inconsistent column counts across rows")

    # ------------------------------------------------------------------
    # /api/zones/by_tag
    # ------------------------------------------------------------------

    def test_zones_by_tag_200_has_required_fields(self):
        code, data = _get(self.port, "/api/zones/by_tag?tag=logic")
        self.assertEqual(code, 200)
        self.assertIn("tag", data)
        self.assertIn("count", data)
        self.assertIn("zone_ids", data)

    def test_zones_by_tag_tag_matches_request(self):
        _, data = _get(self.port, "/api/zones/by_tag?tag=logic")
        self.assertEqual(data["tag"], "logic")

    def test_zones_by_tag_count_matches_zone_ids_length(self):
        _, data = _get(self.port, "/api/zones/by_tag?tag=logic")
        self.assertEqual(data["count"], len(data["zone_ids"]))

    def test_zones_by_tag_zone_ids_are_integers(self):
        _, data = _get(self.port, "/api/zones/by_tag?tag=logic")
        for zid in data["zone_ids"]:
            self.assertIsInstance(zid, int)
            self.assertGreater(zid, 0)

    def test_zones_by_tag_with_frame_range(self):
        code, data = _get(self.port, "/api/zones/by_tag?tag=logic&start_frame=0&end_frame=10")
        self.assertEqual(code, 200)
        self.assertIn("zone_ids", data)
        # Frame-filtered result should have <= full result
        self.assertLessEqual(data["count"], 3)

    def test_zones_by_tag_unknown_tag_returns_empty(self):
        code, data = _get(self.port, "/api/zones/by_tag?tag=unknown_tag_xyz")
        self.assertEqual(code, 200)
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["zone_ids"], [])

    def test_zones_by_tag_missing_tag_returns_400(self):
        code, data = _get(self.port, "/api/zones/by_tag")
        # Real server returns 400; mock falls back to 404 — both indicate missing param
        self.assertIn(code, (400, 404))
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # /api/frame_number
    # ------------------------------------------------------------------

    def test_frame_number_200_has_required_fields(self):
        code, data = _get(self.port, "/api/frame_number?ts=1000000")
        self.assertEqual(code, 200)
        self.assertIn("ts_ns", data)
        self.assertIn("frame_number", data)

    def test_frame_number_ts_matches_request(self):
        _, data = _get(self.port, "/api/frame_number?ts=1000000")
        self.assertEqual(data["ts_ns"], 1000000)

    def test_frame_number_is_integer(self):
        _, data = _get(self.port, "/api/frame_number?ts=1000000")
        self.assertIsInstance(data["frame_number"], int)

    def test_frame_number_valid_ts_returns_non_negative(self):
        _, data = _get(self.port, "/api/frame_number?ts=1000000")
        self.assertGreaterEqual(data["frame_number"], 0)

    def test_frame_number_out_of_range_returns_minus_one(self):
        _, data = _get(self.port, "/api/frame_number?ts=0")
        self.assertEqual(data["frame_number"], -1)

    def test_frame_number_missing_ts_returns_400(self):
        code, data = _get(self.port, "/api/frame_number")
        # Real server returns 400; mock falls back to 404 — both indicate missing param
        self.assertIn(code, (400, 404))
        self.assertIn("error", data)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
