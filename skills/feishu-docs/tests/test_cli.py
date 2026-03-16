import json
import pytest
from unittest.mock import patch, MagicMock
from feishu_fetch import run

_BLOCKS = [{"block_type": 2, "paragraph": {"elements": [{"text_run": {"content": "Hello"}}]}}]

def _mock_fetch(blocks=None):
    blocks = blocks or _BLOCKS
    m = MagicMock(return_value=blocks)
    return m

def test_default_prints_markdown(capsys):
    with patch("feishu_fetch.parse_url", return_value=("tok", "docx")), \
         patch("feishu_fetch.get_token", return_value="t"), \
         patch("feishu_fetch.fetch_blocks", _mock_fetch()):
        run(["https://example.feishu.cn/docx/tok"])
    out = capsys.readouterr().out
    assert "Hello" in out

def test_export_md_writes_file(tmp_path):
    out_file = tmp_path / "out.md"
    with patch("feishu_fetch.parse_url", return_value=("tok", "docx")), \
         patch("feishu_fetch.get_token", return_value="t"), \
         patch("feishu_fetch.fetch_blocks", _mock_fetch()):
        run(["https://example.feishu.cn/docx/tok", "--export-md", str(out_file)])
    assert out_file.read_text(encoding="utf-8").strip() == "Hello"

def test_search_prints_results(capsys):
    with patch("feishu_fetch.parse_url", return_value=("tok", "docx")), \
         patch("feishu_fetch.get_token", return_value="t"), \
         patch("feishu_fetch.fetch_blocks", _mock_fetch()):
        run(["https://example.feishu.cn/docx/tok", "--search", "Hello"])
    out = capsys.readouterr().out
    assert "Hello" in out

def test_json_output(capsys):
    with patch("feishu_fetch.parse_url", return_value=("tok", "docx")), \
         patch("feishu_fetch.get_token", return_value="t"), \
         patch("feishu_fetch.fetch_blocks", _mock_fetch()):
        run(["https://example.feishu.cn/docx/tok", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)

def test_invalid_url_exits_with_error(capsys):
    with pytest.raises(SystemExit) as exc_info:
        run(["https://www.google.com/docx/abc"])
    assert exc_info.value.code != 0

def test_missing_credentials_exits_with_error(capsys):
    with patch("feishu_fetch.parse_url", return_value=("tok", "docx")), \
         patch("feishu_fetch.get_token", side_effect=RuntimeError("未找到飞书凭证")):
        with pytest.raises(SystemExit) as exc_info:
            run(["https://example.feishu.cn/docx/tok"])
    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    assert "错误" in err
