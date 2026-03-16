from feishu.searcher import search

def _para(text: str) -> dict:
    return {"block_type": 2, "paragraph": {"elements": [{"text_run": {"content": text}}]}}

def test_finds_matching_paragraph():
    blocks = [_para("foo"), _para("hello world"), _para("bar")]
    results = search(blocks, "hello")
    assert len(results) == 1
    assert ">>> hello world <<<" in results[0]

def test_includes_context_before_and_after():
    blocks = [_para("before"), _para("match here"), _para("after")]
    results = search(blocks, "match")
    assert "before" in results[0]
    assert "after" in results[0]

def test_no_match_returns_empty():
    blocks = [_para("nothing"), _para("relevant")]
    results = search(blocks, "xyz")
    assert results == []

def test_match_at_start_no_before_context():
    blocks = [_para("match"), _para("next")]
    results = search(blocks, "match")
    assert "next" in results[0]

def test_match_at_end_no_after_context():
    blocks = [_para("prev"), _para("match")]
    results = search(blocks, "match")
    assert "prev" in results[0]

def test_multiple_matches():
    blocks = [_para("match1"), _para("middle"), _para("match2")]
    results = search(blocks, "match")
    assert len(results) == 2

def test_case_insensitive():
    blocks = [_para("Hello World")]
    results = search(blocks, "hello")
    assert len(results) == 1
