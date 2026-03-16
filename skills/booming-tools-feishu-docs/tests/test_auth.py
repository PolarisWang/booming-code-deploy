import time
import pytest
from unittest.mock import patch, MagicMock
import feishu.auth as auth_module

def _make_response(token="test_token", expire=7200):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"tenant_access_token": token, "expire": expire}
    return resp

def setup_function():
    # 每个测试前清空缓存
    auth_module._cache = None

def test_get_token_calls_api(monkeypatch):
    monkeypatch.setenv("FEISHU_APP_ID", "app_id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app_secret")

    with patch("feishu.auth.httpx.post", return_value=_make_response()) as mock_post:
        token = auth_module.get_token()

    assert token == "test_token"
    mock_post.assert_called_once()

def test_token_is_cached(monkeypatch):
    monkeypatch.setenv("FEISHU_APP_ID", "app_id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app_secret")

    with patch("feishu.auth.httpx.post", return_value=_make_response()) as mock_post:
        auth_module.get_token()
        auth_module.get_token()

    # API 只被调用一次
    assert mock_post.call_count == 1

def test_expired_token_is_refreshed(monkeypatch):
    monkeypatch.setenv("FEISHU_APP_ID", "app_id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app_secret")
    # 注入一个已过期的缓存
    auth_module._cache = ("old_token", time.time() - 1)

    with patch("feishu.auth.httpx.post", return_value=_make_response("new_token")) as mock_post:
        token = auth_module.get_token()

    assert token == "new_token"
    assert mock_post.call_count == 1

def test_missing_credentials_raises(monkeypatch):
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    monkeypatch.delenv("FEISHU_APP_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="FEISHU_APP_ID"):
        auth_module.get_token()
