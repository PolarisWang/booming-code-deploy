import pytest
from feishu.parser import parse_url

def test_docx_feishu_url():
    token, doc_type = parse_url("https://example.feishu.cn/docx/AbCdEfGh12345678")
    assert token == "AbCdEfGh12345678"
    assert doc_type == "docx"

def test_wiki_feishu_url():
    token, doc_type = parse_url("https://example.feishu.cn/wiki/WikiToken999")
    assert token == "WikiToken999"
    assert doc_type == "wiki"

def test_larkoffice_url():
    token, doc_type = parse_url("https://example.larkoffice.com/docx/LarkToken123")
    assert token == "LarkToken123"
    assert doc_type == "docx"

def test_url_with_query_params():
    token, doc_type = parse_url("https://example.feishu.cn/docx/Token123?from=share")
    assert token == "Token123"
    assert doc_type == "docx"

def test_unsupported_old_docs_url():
    with pytest.raises(ValueError, match="不支持旧版"):
        parse_url("https://example.feishu.cn/docs/doccnABCDEFG")

def test_non_feishu_url():
    with pytest.raises(ValueError, match="不是有效的飞书链接"):
        parse_url("https://www.google.com/docx/abc")

def test_empty_token():
    with pytest.raises(ValueError, match="无法从 URL 中提取"):
        parse_url("https://example.feishu.cn/docx/")
