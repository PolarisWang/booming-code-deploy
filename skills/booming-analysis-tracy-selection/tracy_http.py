#!/usr/bin/env python3
"""
Tracy Profiler UI HTTP client for agent use.

Usage:
    python tracy_http.py filepath
    python tracy_http.py selection
    python tracy_http.py zone <zone_id>

Outputs JSON to stdout. Exit code 0 = success, 1 = error.
"""

import json
import sys
import urllib.request
import urllib.error

BASE_PORT = 9090
PORT_SCAN_RANGE = 10


def _discover_port() -> int | None:
    """Scan 9090-9099 for a Tracy Profiler UI with a trace file open."""
    for port in range(BASE_PORT, BASE_PORT + PORT_SCAN_RANGE):
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


def _get(port: int, path: str) -> dict:
    """GET request to Tracy UI API, return parsed JSON."""
    url = f"http://localhost:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5.0) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: tracy_http.py <filepath|selection|zone> [zone_id]"}))
        sys.exit(1)

    cmd = sys.argv[1]

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

    else:
        print(json.dumps({"error": f"Unknown command: {cmd}. Use: filepath, selection, zone"}))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))
    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
