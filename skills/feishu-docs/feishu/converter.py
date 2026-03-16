# 飞书 block_type 整数对应关系
_BLOCK_TYPE_PAGE = 1
_BLOCK_TYPE_PARA = 2
_BLOCK_TYPE_HEADING1 = 3
_BLOCK_TYPE_HEADING6 = 8
_BLOCK_TYPE_BULLET = 9
_BLOCK_TYPE_ORDERED = 10
_BLOCK_TYPE_CODE = 11
_BLOCK_TYPE_QUOTE = 12
_BLOCK_TYPE_TABLE = 19
_BLOCK_TYPE_DIVIDER = 22

# 飞书代码语言整数 → 字符串（常用子集）
_CODE_LANG = {
    1: "", 2: "abap", 3: "ada", 4: "apache", 5: "bash", 6: "c", 7: "clojure",
    8: "coffeescript", 9: "cpp", 10: "csharp", 11: "css", 12: "dart", 13: "diff",
    14: "dockerfile", 15: "elixir", 16: "elm", 17: "erlang", 18: "fortran",
    19: "go", 20: "groovy", 21: "haskell", 22: "html", 23: "ini", 24: "java",
    25: "javascript", 26: "json", 27: "kotlin", 28: "latex", 29: "lisp",
    30: "lua", 31: "makefile", 32: "markdown", 33: "matlab", 34: "mermaid",
    35: "nginx", 36: "objectivec", 37: "ocaml", 38: "opencl", 39: "perl",
    40: "php", 41: "powershell", 42: "prolog", 43: "protobuf", 44: "python",
    45: "r", 46: "ruby", 47: "rust", 48: "scala", 49: "shell", 50: "sql",
    51: "swift", 52: "thrift", 53: "toml", 54: "typescript", 55: "vbscript",
    56: "verilog", 57: "vhdl", 58: "visualbasic", 59: "xml", 60: "yaml",
    61: "cmake", 62: "javascript",
}


def _extract_text(elements: list[dict]) -> str:
    """从 elements 数组中提取纯文本。"""
    parts = []
    for el in elements:
        if "text_run" in el:
            parts.append(el["text_run"].get("content", ""))
    return "".join(parts)


def blocks_to_markdown(blocks: list[dict]) -> str:
    """将飞书 block JSON 列表转换为 Markdown 字符串。未知 block 类型静默跳过。"""
    lines: list[str] = []

    for block in blocks:
        bt = block.get("block_type", 0)

        if bt == _BLOCK_TYPE_PAGE:
            continue

        elif bt == _BLOCK_TYPE_PARA:
            text = _extract_text(block.get("paragraph", {}).get("elements", []))
            if text.strip():
                lines.append(text)
                lines.append("")

        elif _BLOCK_TYPE_HEADING1 <= bt <= _BLOCK_TYPE_HEADING6:
            level = bt - 2  # heading1=3 → level=1
            key = f"heading{level}"
            text = _extract_text(block.get(key, {}).get("elements", []))
            lines.append(f"{'#' * level} {text}")
            lines.append("")

        elif bt == _BLOCK_TYPE_BULLET:
            text = _extract_text(block.get("bullet", {}).get("elements", []))
            lines.append(f"- {text}")

        elif bt == _BLOCK_TYPE_ORDERED:
            text = _extract_text(block.get("ordered", {}).get("elements", []))
            lines.append(f"1. {text}")

        elif bt == _BLOCK_TYPE_CODE:
            code_data = block.get("code", {})
            lang = _CODE_LANG.get(code_data.get("language", 1), "")
            text = _extract_text(code_data.get("elements", []))
            lines.append(f"```{lang}")
            lines.append(text)
            lines.append("```")
            lines.append("")

        elif bt == _BLOCK_TYPE_QUOTE:
            text = _extract_text(block.get("quote", {}).get("elements", []))
            lines.append(f"> {text}")
            lines.append("")

        elif bt == _BLOCK_TYPE_TABLE:
            # 飞书 table block 的 cells 仅含子 block ID 列表，内容在子 block 中
            # 简化策略：输出占位符，保证文档不被截断
            lines.append("[table]")
            lines.append("")

        elif bt == _BLOCK_TYPE_DIVIDER:
            lines.append("---")
            lines.append("")

        # 未知类型：静默跳过

    return "\n".join(lines).strip()
