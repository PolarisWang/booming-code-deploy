"""飞书文档写入核心：Markdown → blocks 转换 + API 写入。

参考 https://github.com/huandu/feishu-markdown 的 block type 定义。
写入 API 的 block_type 编号与读取 API 不同：
  Text/Paragraph = 2  (field: text)
  Heading1-6     = 3-8 (field: heading1-heading6)
  Bullet         = 12 (field: bullet)     ← 读取 API 中是 9
  Ordered        = 13 (field: ordered)    ← 读取 API 中是 10
  Code           = 14 (field: code)       ← 读取 API 中是 11
  Quote          = 15 (field: quote)      ← 读取 API 中是 12
  Divider        = 22 (field: divider: {})
"""
import os
import re
import urllib.parse
import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE = "https://open.feishu.cn"
_BATCH_SIZE = 50

# 飞书文档域名，通过 FEISHU_DOMAIN 环境变量配置
_DOC_DOMAIN = os.environ.get("FEISHU_DOMAIN", "boomingtech.feishu.cn")

# 写入 API 使用的 block_type 值（与读取 API 不同）
_BT_TEXT = 2      # 普通段落
_BT_H1 = 3        # 一级标题（H1~H6 对应 3~8）
_BT_BULLET = 12   # 无序列表
_BT_ORDERED = 13  # 有序列表
_BT_CODE = 14     # 代码块
_BT_QUOTE = 15    # 引用
_BT_DIVIDER = 22  # 分割线

# 语言名（小写）→ 飞书 language 整数，与 converter.py 的 _CODE_LANG 反向对齐
_LANG_MAP: dict[str, int] = {
    "python": 44, "py": 44,
    "javascript": 25, "js": 25,
    "typescript": 54, "ts": 54,
    "go": 19, "golang": 19,
    "rust": 47,
    "bash": 5, "sh": 5,
    "shell": 49,
    "json": 26,
    "yaml": 60, "yml": 60,
    "sql": 50,
    "cpp": 9, "c++": 9,
    "c": 6,
    "java": 24,
    "kotlin": 27, "kt": 27,
    "swift": 51,
    "ruby": 46, "rb": 46,
    "php": 40,
    "css": 11,
    "html": 22,
    "xml": 59,
    "markdown": 32, "md": 32,
    "dockerfile": 14,
    "powershell": 41, "ps1": 41,
    "toml": 53,
    "ini": 23,
}

# 行内 Markdown 解析：将文本分解为带样式的 text_run elements
_INLINE_PATTERN = re.compile(
    r"(\*\*(.+?)\*\*"      # **bold**
    r"|__(.+?)__"           # __bold__
    r"|\*(.+?)\*"           # *italic*
    r"|_(.+?)_"             # _italic_
    r"|~~(.+?)~~"           # ~~strikethrough~~
    r"|`(.+?)`"             # `inline_code`
    r"|\[(.+?)\]\((.+?)\)"  # [text](url)
    r")",
    re.DOTALL,
)


def _parse_inline(text: str) -> list[dict]:
    """将行内 Markdown 标记解析为 text_run elements 列表。

    支持：**bold**、*italic*、~~strike~~、`code`、[text](url)
    """
    elements: list[dict] = []
    last = 0

    for m in _INLINE_PATTERN.finditer(text):
        start, end = m.start(), m.end()
        # 匹配前的普通文本
        if start > last:
            elements.append(_plain_run(text[last:start]))

        full = m.group(0)
        if full.startswith("**") or full.startswith("__"):
            content = m.group(2) or m.group(3)
            elements.append(_styled_run(content, bold=True))
        elif full.startswith("~~"):
            content = m.group(6)
            elements.append(_styled_run(content, strikethrough=True))
        elif full.startswith("`"):
            content = m.group(7)
            elements.append(_styled_run(content, inline_code=True))
        elif full.startswith("["):
            link_text = m.group(8)
            link_url = m.group(9)
            # URL decode（飞书 API 要求 URL 编码）
            encoded_url = urllib.parse.quote(link_url, safe=":/?#[]@!$&'()*+,;=")
            elements.append(_link_run(link_text, encoded_url))
        elif full.startswith("*") or full.startswith("_"):
            content = m.group(4) or m.group(5)
            elements.append(_styled_run(content, italic=True))

        last = end

    # 剩余普通文本
    if last < len(text):
        elements.append(_plain_run(text[last:]))

    return elements if elements else [_plain_run(text)]


def _plain_run(content: str) -> dict:
    return {
        "text_run": {
            "content": content,
            "text_element_style": {
                "bold": False, "italic": False, "inline_code": False,
                "strikethrough": False, "underline": False,
            },
        }
    }


def _styled_run(content: str, *, bold=False, italic=False,
                inline_code=False, strikethrough=False, underline=False) -> dict:
    return {
        "text_run": {
            "content": content,
            "text_element_style": {
                "bold": bold, "italic": italic, "inline_code": inline_code,
                "strikethrough": strikethrough, "underline": underline,
            },
        }
    }


def _link_run(content: str, url: str) -> dict:
    return {
        "text_run": {
            "content": content,
            "text_element_style": {
                "bold": False, "italic": False, "inline_code": False,
                "strikethrough": False, "underline": False,
                "link": {"url": url},
            },
        }
    }


def _text_block(block_type: int, field: str, inline_text: str) -> dict:
    """创建带行内样式解析的文本 block。"""
    return {
        "block_type": block_type,
        field: {"elements": _parse_inline(inline_text)},
    }


class PartialWriteError(RuntimeError):
    """批次写入失败，文档已创建但内容不完整。"""
    def __init__(self, message: str, url: str, n_written: int):
        super().__init__(message)
        self.url = url
        self.n_written = n_written


def markdown_to_blocks(md: str) -> list[dict]:
    """将 Markdown 字符串逐行解析为飞书 block JSON 列表。

    支持：标题、段落、无序/有序列表、引用、代码块、分割线、行内样式
    参考 feishu-markdown 库的 block type 编号体系。
    """
    blocks: list[dict] = []
    lines = md.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # 空行跳过
        if not line.strip():
            i += 1
            continue

        # 代码块（``` 开始）
        if line.startswith("```"):
            lang_name = line[3:].strip().lower()
            language = _LANG_MAP.get(lang_name, 1)
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # 跳过结尾 ```
            code_content = "\n".join(code_lines)
            blocks.append({
                "block_type": _BT_CODE,
                "code": {
                    "language": language,
                    "elements": [_plain_run(code_content)],
                },
            })
            continue

        # 分割线 --- / *** / ___
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", line.strip()):
            blocks.append({"block_type": _BT_DIVIDER, "divider": {}})
            i += 1
            continue

        # 标题 # ~ ######
        heading_m = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_m:
            level = len(heading_m.group(1))
            content = heading_m.group(2).strip()
            key = f"heading{level}"
            # heading 用 block_type = level + 2（H1=3, H6=8）
            blocks.append({
                "block_type": _BT_H1 + (level - 1),
                key: {"elements": _parse_inline(content)},
            })
            i += 1
            continue

        # 无序列表 - / *（需在 heading/divider 之后检查，避免 ** 冲突）
        bullet_m = re.match(r"^[-*]\s+(.*)", line)
        if bullet_m:
            blocks.append(_text_block(_BT_BULLET, "bullet", bullet_m.group(1)))
            i += 1
            continue

        # 有序列表 N.
        ordered_m = re.match(r"^\d+\.\s+(.*)", line)
        if ordered_m:
            blocks.append(_text_block(_BT_ORDERED, "ordered", ordered_m.group(1)))
            i += 1
            continue

        # 引用 >
        if line.startswith(">"):
            content = line[1:].lstrip()
            blocks.append(_text_block(_BT_QUOTE, "quote", content))
            i += 1
            continue

        # 普通段落（包含表格行，原样作为文本保留）
        blocks.append(_text_block(_BT_TEXT, "text", line))
        i += 1

    return blocks


def set_document_permission(doc_id: str, token: str,
                             link_share: str = "tenant_readable") -> None:
    """设置文档链接分享权限。

    link_share 可选值：
      "closed"           - 关闭链接分享（默认）
      "tenant_readable"  - 组织内所有人可读（有链接即可访问）
      "tenant_editable"  - 组织内所有人可编辑
      "anyone_readable"  - 所有人可读（含组织外）
      "anyone_editable"  - 所有人可编辑（含组织外）
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = httpx.patch(
        f"{_BASE}/open-apis/drive/v1/permissions/{doc_id}/public",
        params={"type": "docx"},
        json={"link_share_entity": link_share},
        headers=headers,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", 0) != 0:
        # 权限设置失败不阻断流程，只发出警告
        raise RuntimeError(
            f"设置文档权限失败（code={data['code']}）：{data.get('msg')}"
        )


def create_document(title: str, blocks: list[dict], token: str,
                    link_share: str = "tenant_readable",
                    folder_token: str | None = None) -> str:
    """创建飞书文档并写入 blocks，返回文档 URL。

    token 是 tenant_access_token（用于写 blocks）。
    若设置了 FEISHU_USER_ACCESS_TOKEN（通过 feishu_auth.py 获取），
    则创建文档时使用 user_access_token，文档归属用户个人空间。
    folder_token 通过 FEISHU_FOLDER_TOKEN 环境变量或 --folder 参数指定。
    """
    # folder_token 优先用参数，其次读环境变量
    folder_token = folder_token or os.environ.get("FEISHU_FOLDER_TOKEN")

    # user_access_token：用于在个人空间创建文档（有效期 ~2小时）
    user_token = os.environ.get("FEISHU_USER_ACCESS_TOKEN")

    # 有 user_token + folder_token 时，全程用 user token（文档在用户空间）
    # 否则用 tenant token（文档在机器人空间）
    use_user_token = bool(user_token and folder_token)
    create_token = user_token if use_user_token else token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    create_headers = {
        "Authorization": f"Bearer {create_token}",
        "Content-Type": "application/json",
    }

    # 1. 创建空文档（指定 folder_token 则创建在指定文件夹内）
    create_body: dict = {"title": title}
    if folder_token:
        create_body["folder_token"] = folder_token

    resp = httpx.post(
        f"{_BASE}/open-apis/docx/v1/documents",
        json=create_body,
        headers=create_headers,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", 0) != 0:
        raise RuntimeError(
            f"创建文档失败（code={data['code']}）：{data.get('msg')}"
        )
    doc_id = data["data"]["document"]["document_id"]
    doc_url = f"https://{_DOC_DOMAIN}/docx/{doc_id}"

    # 2. 分批写入 blocks（用户空间的文档需要用 user token 写入）
    write_headers = create_headers if use_user_token else headers
    n_written = 0
    for batch_start in range(0, len(blocks), _BATCH_SIZE):
        batch = blocks[batch_start: batch_start + _BATCH_SIZE]
        resp = httpx.post(
            f"{_BASE}/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
            json={"children": batch, "index": -1},
            headers=write_headers,
        )
        resp.raise_for_status()
        write_data = resp.json()
        if write_data.get("code", 0) != 0:
            raise PartialWriteError(
                f"写入 blocks 失败（已写入 {n_written}/{len(blocks)}，"
                f"code={write_data['code']}）：{write_data.get('msg')}",
                url=doc_url,
                n_written=n_written,
            )
        n_written += len(batch)

    # 3. 设置链接分享权限（用户空间的文档用 user token 设置）
    perm_token = create_token if use_user_token else token
    if link_share != "closed":
        try:
            set_document_permission(doc_id, perm_token, link_share)
        except RuntimeError:
            pass  # 权限设置失败不阻断，文档已创建成功

    return doc_url
