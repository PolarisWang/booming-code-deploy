#!/usr/bin/env python3
"""
Tracy Profiler 配置与启动工具。

Usage:
    python tracy_config.py get                        # 读取 tracy_profiler_path
    python tracy_config.py set <path>                 # 保存 tracy_profiler_path
    python tracy_config.py validate <path>            # 验证可执行文件是否存在
    python tracy_config.py launch <trace_file>        # 用配置的路径启动 Tracy 并打开 trace 文件

配置文件位置：.booming/settings/booming-analysis-tracy.json（相对于当前工作目录）
"""

import json
import os
import pathlib
import subprocess
import sys

CONFIG_REL_PATH = pathlib.Path(".booming") / "settings" / "booming-analysis-tracy.json"


def _config_path() -> pathlib.Path:
    return pathlib.Path.cwd() / CONFIG_REL_PATH


def _read_config() -> dict:
    p = _config_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _write_config(config: dict) -> None:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_get() -> None:
    """读取并输出 tracy_profiler_path，未配置时输出空字符串。"""
    config = _read_config()
    path = config.get("tracy_profiler_path", "")
    print(json.dumps({"tracy_profiler_path": path, "config_file": str(_config_path())}))


def cmd_set(profiler_path: str) -> None:
    """保存 tracy_profiler_path 到配置文件。"""
    config = _read_config()
    config["tracy_profiler_path"] = profiler_path
    _write_config(config)
    print(json.dumps({"saved": True, "tracy_profiler_path": profiler_path, "config_file": str(_config_path())}))


def cmd_validate(path: str) -> None:
    """检查可执行文件是否存在。"""
    exists = pathlib.Path(path).is_file()
    print(json.dumps({"path": path, "exists": exists}))
    sys.exit(0 if exists else 1)


def cmd_launch(trace_file: str) -> None:
    """从配置中读取 Tracy Profiler 路径并启动，打开指定 trace 文件。"""
    config = _read_config()
    profiler_path = config.get("tracy_profiler_path", "")

    if not profiler_path:
        print(json.dumps({"error": "tracy_profiler_path not configured. Run: tracy_config.py set <path>"}))
        sys.exit(1)

    if not pathlib.Path(profiler_path).is_file():
        print(json.dumps({"error": f"Tracy Profiler not found: {profiler_path}"}))
        sys.exit(1)

    if not pathlib.Path(trace_file).exists():
        print(json.dumps({"error": f"Trace file not found: {trace_file}"}))
        sys.exit(1)

    subprocess.Popen([profiler_path, trace_file])
    print(json.dumps({"launched": True, "profiler": profiler_path, "trace_file": trace_file}))


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: tracy_config.py <get|set|validate|launch> [args]"}))
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "get":
        cmd_get()
    elif cmd == "set":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: tracy_config.py set <profiler_path>"}))
            sys.exit(1)
        cmd_set(sys.argv[2])
    elif cmd == "validate":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: tracy_config.py validate <path>"}))
            sys.exit(1)
        cmd_validate(sys.argv[2])
    elif cmd == "launch":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: tracy_config.py launch <trace_file>"}))
            sys.exit(1)
        cmd_launch(sys.argv[2])
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}. Use: get, set, validate, launch"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
