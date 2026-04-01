import pytest
from unittest.mock import patch, MagicMock
from feishu.writer import markdown_to_blocks, create_document

def _style():
    return {"bold": False, "italic": False, "inline_code": False,
            "strikethrough": False, "underline": False}

def _text_run(content):
    return {"text_run": {"content": content, "text_element_style": _style()}}

def _block(bt, field, content):
    return {"block_type": bt, field: {"elements": [_text_run(content)]}}

def test_empty_string_returns_empty_list():
    assert markdown_to_blocks("") == []

def test_blank_lines_skipped():
    assert markdown_to_blocks("\n\n\n") == []

def test_paragraph():
    blocks = markdown_to_blocks("Hello world")
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 2
    assert blocks[0]["paragraph"]["elements"][0]["text_run"]["content"] == "Hello world"

def test_heading_levels():
    for level in range(1, 7):
        md = "#" * level + " Title"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["block_type"] == level + 2
        key = f"heading{level}"
        assert key in blocks[0]
        assert blocks[0][key]["elements"][0]["text_run"]["content"] == "Title"

def test_bullet_list():
    blocks = markdown_to_blocks("- Item A")
    assert blocks[0]["block_type"] == 9
    assert blocks[0]["bullet"]["elements"][0]["text_run"]["content"] == "Item A"

def test_bullet_star():
    blocks = markdown_to_blocks("* Item B")
    assert blocks[0]["block_type"] == 9

def test_ordered_list():
    blocks = markdown_to_blocks("1. Step one")
    assert blocks[0]["block_type"] == 10
    assert blocks[0]["ordered"]["elements"][0]["text_run"]["content"] == "Step one"

def test_ordered_list_any_number():
    blocks = markdown_to_blocks("3. Third item")
    assert blocks[0]["block_type"] == 10

def test_quote():
    blocks = markdown_to_blocks("> Quoted text")
    assert blocks[0]["block_type"] == 12
    assert blocks[0]["quote"]["elements"][0]["text_run"]["content"] == "Quoted text"

def test_code_block_python():
    md = "```python\nprint('hi')\n```"
    blocks = markdown_to_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 11
    assert blocks[0]["code"]["language"] == 44
    assert blocks[0]["code"]["elements"][0]["text_run"]["content"] == "print('hi')"

def test_code_block_unknown_language():
    md = "```brainfuck\n++++\n```"
    blocks = markdown_to_blocks(md)
    assert blocks[0]["code"]["language"] == 1

def test_code_block_no_language():
    md = "```\nsome code\n```"
    blocks = markdown_to_blocks(md)
    assert blocks[0]["code"]["language"] == 1

def test_divider_dashes():
    blocks = markdown_to_blocks("---")
    assert blocks[0]["block_type"] == 22

def test_divider_stars():
    blocks = markdown_to_blocks("***")
    assert blocks[0]["block_type"] == 22

def test_divider_underscores():
    blocks = markdown_to_blocks("___")
    assert blocks[0]["block_type"] == 22

def test_table_row_downgraded_to_paragraph():
    blocks = markdown_to_blocks("| col1 | col2 |")
    assert blocks[0]["block_type"] == 2
    content = blocks[0]["paragraph"]["elements"][0]["text_run"]["content"]
    assert "|" in content
    assert "col1" in content

def test_inline_markdown_written_as_literal_text():
    blocks = markdown_to_blocks("**bold** and *italic*")
    assert blocks[0]["block_type"] == 2
    content = blocks[0]["paragraph"]["elements"][0]["text_run"]["content"]
    assert "**bold**" in content
    style = blocks[0]["paragraph"]["elements"][0]["text_run"]["text_element_style"]
    assert style["bold"] is False
    assert style["italic"] is False

def test_text_element_style_all_false():
    blocks = markdown_to_blocks("Normal text")
    style = blocks[0]["paragraph"]["elements"][0]["text_run"]["text_element_style"]
    assert all(v is False for v in style.values())

def test_multiline_document():
    md = "# Title\n\nParagraph text\n\n- bullet\n\n1. ordered"
    blocks = markdown_to_blocks(md)
    types = [b["block_type"] for b in blocks]
    assert 3 in types
    assert 2 in types
    assert 9 in types
    assert 10 in types

def _make_resp(body):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = body
    return resp

def test_create_document_returns_url():
    create_resp = _make_resp({"code": 0, "data": {"document": {"document_id": "doc123"}}})
    write_resp = _make_resp({"code": 0, "data": {}})
    blocks = [{"block_type": 2, "paragraph": {"elements": [{"text_run": {"content": "hi", "text_element_style": {}}}]}}]
    with patch("feishu.writer.httpx.post", side_effect=[create_resp, write_resp]):
        url = create_document("My Title", blocks, "token")
    assert url == "https://boomingtech.feishu.cn/docx/doc123"

def test_create_document_batches_at_50():
    create_resp = _make_resp({"code": 0, "data": {"document": {"document_id": "docX"}}})
    write_resp = _make_resp({"code": 0, "data": {}})
    blocks = [{"block_type": 22}] * 51
    with patch("feishu.writer.httpx.post", side_effect=[create_resp, write_resp, write_resp]) as mock_post:
        create_document("Title", blocks, "token")
    assert mock_post.call_count == 3

def test_create_document_api_error_raises():
    create_resp = _make_resp({"code": 99991672, "msg": "Access denied"})
    with patch("feishu.writer.httpx.post", return_value=create_resp):
        with pytest.raises(RuntimeError, match="99991672"):
            create_document("Title", [], "token")

def test_create_document_empty_blocks():
    create_resp = _make_resp({"code": 0, "data": {"document": {"document_id": "docY"}}})
    with patch("feishu.writer.httpx.post", return_value=create_resp) as mock_post:
        url = create_document("Empty", [], "token")
    assert mock_post.call_count == 1
    assert url == "https://boomingtech.feishu.cn/docx/docY"

def test_partial_batch_failure_raises_partial_write_error():
    from feishu.writer import PartialWriteError
    create_resp = _make_resp({"code": 0, "data": {"document": {"document_id": "docZ"}}})
    success_resp = _make_resp({"code": 0, "data": {}})
    fail_resp = _make_resp({"code": 99991663, "msg": "token invalid"})
    blocks = [{"block_type": 22}] * 101
    with patch("feishu.writer.httpx.post", side_effect=[create_resp, success_resp, fail_resp]):
        with pytest.raises(PartialWriteError) as exc_info:
            create_document("Title", blocks, "token")
    err = exc_info.value
    assert "https://boomingtech.feishu.cn/docx/docZ" in err.url
    assert err.n_written == 50
