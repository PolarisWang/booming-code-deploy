#!/usr/bin/env python3
"""飞书用户授权工具 — 获取个人空间 folder_token 或临时 user_access_token。

用法：
  python feishu_auth.py            # 浏览器登录，只写入 FEISHU_FOLDER_TOKEN 到 .env
  python feishu_auth.py --print    # 只打印 token，不写文件

说明：
  feishu_write.py 每次上传到个人空间时会自动调用 get_user_token()
  获取临时 user_access_token，不保存到 .env。
"""
import argparse
import base64
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(__file__))

import httpx
from dotenv import load_dotenv, set_key

load_dotenv()

_BASE = "https://open.feishu.cn"
_CALLBACK_PATH = "/feishu_callback"
_PORT = 18726


def _get_app_access_token() -> str:
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    resp = httpx.post(
        f"{_BASE}/open-apis/auth/v3/app_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", 0) != 0:
        raise RuntimeError(f"获取 app_access_token 失败（code={data['code']}）")
    return data["app_access_token"]


def _exchange_code_for_token(code: str) -> str:
    """用 authorization code 换取 user_access_token。"""
    app_token = _get_app_access_token()
    resp = httpx.post(
        f"{_BASE}/open-apis/authen/v1/access_token",
        json={
            "grant_type": "authorization_code",
            "app_access_token": app_token,
            "code": code,
        },
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", 0) != 0:
        raise RuntimeError(f"换取 user_access_token 失败（code={data['code']}）：{data.get('msg')}")
    token_data = data.get("data", data)
    return token_data.get("access_token") or token_data.get("user_access_token")


def _get_personal_folder_token(user_access_token: str) -> str:
    resp = httpx.get(
        f"{_BASE}/open-apis/drive/explorer/v2/root_folder/meta",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", 0) != 0:
        raise RuntimeError(f"获取个人空间失败（code={data['code']}）：{data.get('msg')}")
    return data["data"]["token"]


def get_user_token(silent: bool = False) -> str:
    """通过浏览器 OAuth 获取临时 user_access_token（不保存到 .env）。

    每次调用都会弹出浏览器要求用户授权。
    silent=True 时不打印提示信息（用于 feishu_write.py 内部调用）。
    """
    auth_code: list[str] = []
    auth_event = threading.Event()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == _CALLBACK_PATH:
                params = parse_qs(parsed.query)
                if "code" in params:
                    auth_code.append(params["code"][0])
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        "<html><body style='font-family:sans-serif;text-align:center;padding:50px'>"
                        "<h2 style='color:#28a745'>&#10003; 授权成功！</h2>"
                        "<p>请回到命令行继续。</p>"
                        "<script>window.close();</script>"
                        "</body></html>".encode("utf-8")
                    )
            auth_event.set()

        def log_message(self, format, *args):
            pass

    app_id = os.environ.get("FEISHU_APP_ID", "")
    if not app_id:
        raise RuntimeError("未找到 FEISHU_APP_ID，请先配置 .env")

    redirect_uri = f"http://localhost:{_PORT}{_CALLBACK_PATH}"
    auth_url = (
        f"{_BASE}/open-apis/authen/v1/authorize"
        f"?app_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=drive:drive docx:document"
    )

    server = HTTPServer(("localhost", _PORT), _Handler)
    t = threading.Thread(target=server.handle_request)
    t.daemon = True
    t.start()

    if not silent:
        print("正在打开浏览器进行飞书授权...")
        print(f"若未自动打开，请访问：\n  {auth_url}\n")
    webbrowser.open(auth_url)

    auth_event.wait(timeout=60)

    if not auth_code:
        raise RuntimeError("授权超时或取消")

    if not silent:
        print("授权成功，正在获取 token...")

    return _exchange_code_for_token(auth_code[0])


def run(argv: list[str] | None = None) -> None:
    """CLI 入口：初次配置，写入 FEISHU_FOLDER_TOKEN 到 .env。"""
    parser = argparse.ArgumentParser(description="飞书用户授权，写入个人空间 folder_token")
    parser.add_argument("--print", action="store_true", dest="print_only",
                        help="只打印 token，不写入 .env")
    args = parser.parse_args(argv)

    try:
        user_token = get_user_token()
        folder_token = _get_personal_folder_token(user_token)
    except RuntimeError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"网络错误：{e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n个人空间 folder_token：{folder_token}")

    if args.print_only:
        return

    # 只写入 folder_token，user_access_token 不持久化
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    set_key(env_path, "FEISHU_FOLDER_TOKEN", folder_token)
    print(f"\n[OK] 已写入 {env_path}")
    print("     后续每次 feishu_write.py 上传时会自动弹出浏览器授权。")


if __name__ == "__main__":
    run()
