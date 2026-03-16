import time
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
_REFRESH_BEFORE_SECS = 300  # 提前 5 分钟刷新

_cache: tuple[str, float] | None = None


def get_token() -> str:
    """返回有效的 tenant_access_token，自动刷新。"""
    global _cache

    if _cache is not None:
        token, expire_at = _cache
        if time.time() < expire_at:
            return token

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise RuntimeError(
            "未找到飞书凭证，请设置环境变量：\n"
            "  FEISHU_APP_ID=cli_xxx\n"
            "  FEISHU_APP_SECRET=xxx\n"
            "可在 .env 文件中配置，或直接导出到环境变量。"
        )

    resp = httpx.post(
        _TOKEN_URL,
        json={"app_id": app_id, "app_secret": app_secret},
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code", 0) != 0:
        raise RuntimeError(f"获取 token 失败（code={data['code']}）：{data.get('msg')}")

    token = data["tenant_access_token"]
    expire_secs = data.get("expire", 7200)
    expire_at = time.time() + expire_secs - _REFRESH_BEFORE_SECS
    _cache = (token, expire_at)
    return token
