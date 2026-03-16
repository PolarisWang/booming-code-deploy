def _block_to_text(block: dict) -> str | None:
    """从 block 中提取纯文本，不支持的类型返回 None。"""
    bt = block.get("block_type", 0)
    key_map = {
        2: "paragraph", 3: "heading1", 4: "heading2", 5: "heading3",
        6: "heading4", 7: "heading5", 8: "heading6",
        9: "bullet", 10: "ordered", 11: "code", 12: "quote",
    }
    key = key_map.get(bt)
    if not key:
        return None
    elements = block.get(key, {}).get("elements", [])
    parts = [el["text_run"]["content"] for el in elements if "text_run" in el]
    text = "".join(parts).strip()
    return text if text else None


def search(blocks: list[dict], keyword: str) -> list[str]:
    """在文档 blocks 中搜索关键词，返回包含上下文的匹配段落列表。

    每个结果格式：
        [前一段]
        >>> 匹配段 <<<
        [后一段]
    """
    paragraphs: list[str] = []
    for block in blocks:
        text = _block_to_text(block)
        if text is not None:
            paragraphs.append(text)

    kw_lower = keyword.lower()
    results: list[str] = []

    for i, para in enumerate(paragraphs):
        if kw_lower not in para.lower():
            continue

        parts: list[str] = []
        if i > 0:
            parts.append(paragraphs[i - 1])
        parts.append(f">>> {para} <<<")
        if i < len(paragraphs) - 1:
            parts.append(paragraphs[i + 1])

        results.append("\n".join(parts))

    return results
