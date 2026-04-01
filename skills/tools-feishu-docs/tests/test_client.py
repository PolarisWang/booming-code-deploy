import pytest
from unittest.mock import patch, MagicMock
from feishu.client import fetch_blocks

BASE = "https://open.feishu.cn"

def _make_resp(items, has_more=False, page_token=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    body = {"code": 0, "data": {"items": items, "has_more": has_more}}
    if page_token:
        body["data"]["page_token"] = page_token
    resp.json.return_value = body
    return resp

def test_docx_single_page():
    blocks = [{"block_id": "1", "block_type": 1}]
    with patch("feishu.client.httpx.get", return_value=_make_resp(blocks)) as mock_get:
        result = fetch_blocks("docxToken", "docx", "tok")
    assert result == blocks
    url = mock_get.call_args[0][0]
    assert "/docx/v1/documents/docxToken/blocks" in url

def test_docx_multi_page():
    page1 = [{"block_id": "1"}]
    page2 = [{"block_id": "2"}]
    responses = [
        _make_resp(page1, has_more=True, page_token="cursor1"),
        _make_resp(page2, has_more=False),
    ]
    with patch("feishu.client.httpx.get", side_effect=responses):
        result = fetch_blocks("docxToken", "docx", "tok")
    assert result == page1 + page2

def test_wiki_resolves_docx_token():
    wiki_resp = MagicMock()
    wiki_resp.raise_for_status = MagicMock()
    wiki_resp.json.return_value = {
        "code": 0,
        "data": {"node": {"obj_token": "realDocxToken", "obj_type": "docx"}}
    }
    blocks = [{"block_id": "b1"}]
    docx_resp = _make_resp(blocks)

    with patch("feishu.client.httpx.get", side_effect=[wiki_resp, docx_resp]) as mock_get:
        result = fetch_blocks("wikiToken", "wiki", "tok")

    assert result == blocks
    first_call_url = mock_get.call_args_list[0][0][0]
    assert "/wiki/v2/spaces/get_node" in first_call_url

def test_wiki_non_docx_type_raises():
    wiki_resp = MagicMock()
    wiki_resp.raise_for_status = MagicMock()
    wiki_resp.json.return_value = {
        "code": 0,
        "data": {"node": {"obj_token": "tok", "obj_type": "sheet"}}
    }
    with patch("feishu.client.httpx.get", return_value=wiki_resp):
        with pytest.raises(ValueError, match="不支持此类型"):
            fetch_blocks("wikiToken", "wiki", "tok")

def test_api_error_raises():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"code": 99991663, "msg": "token invalid"}
    with patch("feishu.client.httpx.get", return_value=resp):
        with pytest.raises(RuntimeError, match="99991663"):
            fetch_blocks("docxToken", "docx", "tok")

def test_wiki_api_error_raises():
    wiki_resp = MagicMock()
    wiki_resp.raise_for_status = MagicMock()
    wiki_resp.json.return_value = {"code": 99991663, "msg": "token invalid"}
    with patch("feishu.client.httpx.get", return_value=wiki_resp):
        with pytest.raises(RuntimeError, match="99991663"):
            fetch_blocks("wikiToken", "wiki", "tok")
