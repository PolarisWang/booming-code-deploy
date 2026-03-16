from feishu.converter import blocks_to_markdown

def _block(block_type: int, **kwargs) -> dict:
    return {"block_type": block_type, **kwargs}

def _para(text: str) -> dict:
    return _block(2, paragraph={"elements": [{"text_run": {"content": text}}]})

def _heading(level: int, text: str) -> dict:
    key = f"heading{level}"
    return _block(2 + level, **{key: {"elements": [{"text_run": {"content": text}}]}})

def test_paragraph():
    blocks = [_para("Hello world")]
    md = blocks_to_markdown(blocks)
    assert "Hello world" in md

def test_headings():
    for level in range(1, 7):
        blocks = [_heading(level, f"Title {level}")]
        md = blocks_to_markdown(blocks)
        assert f"{'#' * level} Title {level}" in md

def test_bullet():
    blocks = [_block(9, bullet={"elements": [{"text_run": {"content": "Item A"}}]})]
    md = blocks_to_markdown(blocks)
    assert "- Item A" in md

def test_ordered():
    blocks = [_block(10, ordered={"elements": [{"text_run": {"content": "Step 1"}}]})]
    md = blocks_to_markdown(blocks)
    assert "1. Step 1" in md

def test_code_block():
    blocks = [_block(11, code={"language": 1, "elements": [{"text_run": {"content": "print('hi')"}}]})]
    md = blocks_to_markdown(blocks)
    assert "```" in md
    assert "print('hi')" in md

def test_quote():
    blocks = [_block(12, quote={"elements": [{"text_run": {"content": "Quoted text"}}]})]
    md = blocks_to_markdown(blocks)
    assert "> Quoted text" in md

def test_divider():
    blocks = [_block(22)]
    md = blocks_to_markdown(blocks)
    assert "---" in md

def test_unknown_block_is_skipped():
    blocks = [_para("before"), _block(999), _para("after")]
    md = blocks_to_markdown(blocks)
    assert "before" in md
    assert "after" in md

def test_multiple_text_runs():
    block = _block(2, paragraph={"elements": [
        {"text_run": {"content": "Hello "}},
        {"text_run": {"content": "world"}},
    ]})
    md = blocks_to_markdown([block])
    assert "Hello world" in md

def test_table_block():
    # 飞书 table block 的 cells 字段仅含子 block ID 列表，内容在子 block 中
    # 规格说"简化为 Markdown 表格"，但由于 cells 不含文本内容，
    # 实现策略为输出 [table] 占位符（有意偏差，保证不截断文档）
    block = _block(19, table={"cells": ["cell1", "cell2"]})
    md = blocks_to_markdown([block])
    assert "[table]" in md

def test_empty_blocks():
    assert blocks_to_markdown([]) == ""
