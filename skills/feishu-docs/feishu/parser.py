import re
from urllib.parse import urlparse

_FEISHU_HOSTS = re.compile(r"(.+\.)?(feishu\.cn|larkoffice\.com)$")
_OLD_DOCS_PATH = re.compile(r"^/docs/")
_PATH_PATTERN = re.compile(r"^/(docx|wiki)/([A-Za-z0-9_-]+)")

def parse_url(url: str) -> tuple[str, str]:
    """解析飞书分享链接，返回 (doc_token, doc_type)。

    doc_type 为 "docx" 或 "wiki"。
    不支持的格式抛出 ValueError。
    """
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if not _FEISHU_HOSTS.search(host):
        raise ValueError(f"不是有效的飞书链接：{url}\n支持的域名：*.feishu.cn, *.larkoffice.com")

    path = parsed.path.rstrip("/")

    if _OLD_DOCS_PATH.match(path):
        raise ValueError(
            f"不支持旧版 /docs/ 格式 URL：{url}\n"
            "请在飞书中打开文档，复制新版分享链接（路径为 /docx/ 或 /wiki/）"
        )

    # 匹配 /docx/<token> 或 /wiki/<token>
    m = _PATH_PATTERN.match(path)
    if not m:
        raise ValueError(
            f"无法从 URL 中提取文档 token：{url}\n"
            "支持格式：\n"
            "  https://*.feishu.cn/docx/<token>\n"
            "  https://*.feishu.cn/wiki/<token>\n"
            "  https://*.larkoffice.com/docx/<token>"
        )

    doc_type = m.group(1)   # "docx" or "wiki"
    doc_token = m.group(2)
    return doc_token, doc_type
