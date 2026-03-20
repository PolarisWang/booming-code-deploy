#!/usr/bin/env python3
"""
Tracy Profiler UI HTTP client for agent use.

Usage:
    python tracy_http.py filepath
    python tracy_http.py selection
    python tracy_http.py zone <zone_id>
    python tracy_http.py trace_overview
    python tracy_http.py threads
    python tracy_http.py frames [offset] [count]

Outputs JSON to stdout. Exit code 0 = success, 1 = error.
"""

import json
import sys
import urllib.request
import urllib.error
import urllib.parse

BASE_PORT = 9090
PORT_SCAN_RANGE = 10

import os as _os
_ENV_TEST_PORT = _os.environ.get("TRACY_TEST_PORT")


def _discover_port() -> int | None:
    """Scan 9090-9099 for a Tracy Profiler UI with a trace file open.
    If env var TRACY_TEST_PORT is set, only scan that single port (for testing).
    """
    if _ENV_TEST_PORT:
        scan = [int(_ENV_TEST_PORT)]
    else:
        scan = range(BASE_PORT, BASE_PORT + PORT_SCAN_RANGE)
    for port in scan:
        try:
            url = f"http://localhost:{port}/api/filepath"
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read())
                    if data.get("filepath", ""):
                        return port
        except Exception:
            continue
    return None


def _list_all_instances() -> list:
    """Scan 9090-9099 and return all Tracy instances that have a trace file open."""
    if _ENV_TEST_PORT:
        scan = [int(_ENV_TEST_PORT)]
    else:
        scan = range(BASE_PORT, BASE_PORT + PORT_SCAN_RANGE)
    instances = []
    for port in scan:
        try:
            url = f"http://localhost:{port}/api/filepath"
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read())
                    fp = data.get("filepath", "")
                    if fp:
                        instances.append({"port": port, "filepath": fp})
        except Exception:
            continue
    return instances


def _fix_json(raw: bytes) -> dict:
    """Try to parse JSON, falling back to fixing a known server-side bug
    where each child zone object has an extra closing brace:
      }},{ instead of },{   and   }}]} instead of }]}
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        text = raw.decode("utf-8", errors="replace")
        # Each zone object ends with }} instead of } before , or ]
        fixed = re.sub(r'\}\}([,\]])', r'}\1', text)
        return json.loads(fixed)


def _get(port: int, path: str) -> dict:
    """GET request to Tracy UI API, return parsed JSON."""
    url = f"http://localhost:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5.0) as resp:
            return _fix_json(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _get_raw(port: int, path: str) -> str:
    """GET request, return raw response text (for CSV endpoint)."""
    url = f"http://localhost:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=30.0) as resp:
            return resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": f"HTTP {e.code}: {e.reason}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: tracy_http.py <filepath|selection|zone|trace_overview|trace_info|threads|frames|zone_children|messages|plots|plot_count|plot_values|pools|pool_overview|pool_allocations|pool_callstack_tree|stats_summary|stats_frame_tags|stats_export_csv> [args]"}))
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        instances = _list_all_instances()
        print(json.dumps({"instances": instances}, ensure_ascii=False))
        sys.exit(0)

    port = _discover_port()
    if port is None:
        print(json.dumps({
            "error": "Tracy Profiler UI not found on ports 9090-9099. Open Tracy Profiler and load a trace file."
        }))
        sys.exit(1)

    if cmd == "filepath":
        result = _get(port, "/api/filepath")
        result["port"] = port

    elif cmd == "selection":
        result = _get(port, "/api/current_selection")
        result["port"] = port

    elif cmd == "zone":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: tracy_http.py zone <zone_id>"}))
            sys.exit(1)
        zone_id = sys.argv[2]
        result = _get(port, f"/api/zone/{zone_id}")
        result["port"] = port

    elif cmd == "trace_overview":
        # Returns trace metadata: captured_program, host_info, first_time, last_time,
        # zone_count, frame_count, lock_count, plot_count, message_count, context_switch_count.
        result = _get(port, "/api/trace_overview")
        result["port"] = port

    elif cmd == "trace_info":
        # Returns detailed trace info: host, cpu, timing, app_info, cpu_topology,
        # frame_stats, trace_stats.
        result = _get(port, "/api/trace_info")
        result["port"] = port

    elif cmd == "threads":
        # Returns list of all threads: [{thread_id, thread_name}, ...]
        result = _get(port, "/api/threads")
        result["port"] = port

    elif cmd == "frames":
        # Returns paginated frame list with timing.
        # Optional args: offset (default 0), count (default 100, max 1000).
        offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        result = _get(port, f"/api/frames?offset={offset}&count={count}")
        result["port"] = port

    elif cmd == "zone_children":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: tracy_http.py zone_children <zone_id>"}))
            sys.exit(1)
        zone_id = sys.argv[2]
        result = _get(port, f"/api/zone/{zone_id}/children")
        result["port"] = port

    elif cmd == "messages":
        # Optional args: offset count start_ns end_ns
        offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        params = f"offset={offset}&count={count}"
        if len(sys.argv) > 4:
            params += f"&start={sys.argv[4]}"
        if len(sys.argv) > 5:
            params += f"&end={sys.argv[5]}"
        result = _get(port, f"/api/messages?{params}")
        result["port"] = port

    elif cmd == "plots":
        result = _get(port, "/api/plots")
        result["port"] = port

    elif cmd == "plot_count":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: tracy_http.py plot_count <name>"}))
            sys.exit(1)
        name = urllib.parse.quote(sys.argv[2], safe='')
        result = _get(port, f"/api/plots/{name}/count")
        result["port"] = port

    elif cmd == "plot_values":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: tracy_http.py plot_values <name> [offset] [count] [start_ns] [end_ns]"}))
            sys.exit(1)
        name = urllib.parse.quote(sys.argv[2], safe='')
        offset = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        count = int(sys.argv[4]) if len(sys.argv) > 4 else 100
        params = f"offset={offset}&count={count}"
        if len(sys.argv) > 5:
            params += f"&start={sys.argv[5]}"
        if len(sys.argv) > 6:
            params += f"&end={sys.argv[6]}"
        result = _get(port, f"/api/plots/{name}/values?{params}")
        result["port"] = port

    elif cmd == "pools":
        result = _get(port, "/api/memory/pools")
        result["port"] = port

    elif cmd == "pool_overview":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: tracy_http.py pool_overview <pool> <start_ns> <end_ns>"}))
            sys.exit(1)
        pool = urllib.parse.quote(sys.argv[2], safe='')
        result = _get(port, f"/api/memory/{pool}/overview?start={sys.argv[3]}&end={sys.argv[4]}")
        result["port"] = port

    elif cmd == "pool_allocations":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: tracy_http.py pool_allocations <pool> <start_ns> <end_ns> [offset] [count] [sort]"}))
            sys.exit(1)
        pool = urllib.parse.quote(sys.argv[2], safe='')
        offset = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        count = int(sys.argv[6]) if len(sys.argv) > 6 else 20
        sort = sys.argv[7] if len(sys.argv) > 7 else "none"
        result = _get(port, f"/api/memory/{pool}/allocations?start={sys.argv[3]}&end={sys.argv[4]}&offset={offset}&count={count}&sort={sort}")
        result["port"] = port

    elif cmd == "pool_callstack_tree":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: tracy_http.py pool_callstack_tree <pool> <include_active> <include_inactive> [start_ns] [end_ns]"}))
            sys.exit(1)
        pool = urllib.parse.quote(sys.argv[2], safe='')
        params = f"include_active={sys.argv[3]}&include_inactive={sys.argv[4]}"
        if len(sys.argv) > 5:
            params += f"&start={sys.argv[5]}"
        if len(sys.argv) > 6:
            params += f"&end={sys.argv[6]}"
        result = _get(port, f"/api/memory/{pool}/callstack_tree?{params}")
        result["port"] = port

    elif cmd == "stats_summary":
        result = _get(port, "/api/stats/summary")
        result["port"] = port

    elif cmd == "stats_frame_tags":
        result = _get(port, "/api/stats/frame_tags")
        # stats_frame_tags returns a JSON array; wrap it so port can be attached
        if isinstance(result, list):
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(0)

    elif cmd == "stats_export_csv":
        # Returns raw CSV text, not JSON
        csv_text = _get_raw(port, "/api/stats/export_csv")
        print(csv_text, end="")
        sys.exit(0)

    elif cmd == "zones_by_tag":
        # Usage: zones_by_tag <tag_name> [start_frame] [end_frame]
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: tracy_http.py zones_by_tag <tag_name> [start_frame] [end_frame]"}))
            sys.exit(1)
        tag = urllib.parse.quote(sys.argv[2], safe='')
        params = f"tag={tag}"
        if len(sys.argv) > 3:
            params += f"&start_frame={sys.argv[3]}"
        if len(sys.argv) > 4:
            params += f"&end_frame={sys.argv[4]}"
        result = _get(port, f"/api/zones/by_tag?{params}")
        result["port"] = port

    elif cmd == "frame_number":
        # Usage: frame_number <timestamp_ns>
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: tracy_http.py frame_number <timestamp_ns>"}))
            sys.exit(1)
        result = _get(port, f"/api/frame_number?ts={sys.argv[2]}")
        result["port"] = port

    else:
        print(json.dumps({"error": f"Unknown command: {cmd}. Use: filepath, selection, zone, trace_overview, trace_info, threads, frames, zone_children, messages, plots, plot_count, plot_values, pools, pool_overview, pool_allocations, pool_callstack_tree, stats_summary, stats_frame_tags, stats_export_csv, zones_by_tag, frame_number"}))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))
    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
