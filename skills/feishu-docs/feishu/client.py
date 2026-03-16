import httpx

_BASE = "https://open.feishu.cn"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _resolve_wiki_token(wiki_token: str, token: str) -> str:
    """将 wiki token 转换为真实的 docx token。"""
    url = f"{_BASE}/open-apis/wiki/v2/spaces/get_node"
    resp = httpx.get(url, params={"token": wiki_token}, headers=_headers(token))
    resp.raise_for_status()
    data = resp.json()

    if data.get("code", 0) != 0:
        raise RuntimeError(f"获取 wiki node 失败（code={data['code']}）：{data.get('msg')}")

    node = data["data"]["node"]
    obj_type = node.get("obj_type", "")
    if obj_type != "docx":
        raise ValueError(
            f"不支持此类型的 wiki 节点（obj_type={obj_type}），仅支持 docx 类型。"
        )
    return node["obj_token"]


def fetch_blocks(doc_token: str, doc_type: str, token: str) -> list[dict]:
    """拉取文档所有 block，自动处理分页与 wiki 类型转换。"""
    if doc_type == "wiki":
        doc_token = _resolve_wiki_token(doc_token, token)

    url = f"{_BASE}/open-apis/docx/v1/documents/{doc_token}/blocks"
    all_items: list[dict] = []
    page_token: str | None = None

    while True:
        params: dict = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token

        resp = httpx.get(url, params=params, headers=_headers(token))
        resp.raise_for_status()
        data = resp.json()

        if data.get("code", 0) != 0:
            raise RuntimeError(f"获取 blocks 失败（code={data['code']}）：{data.get('msg')}")

        items = data["data"].get("items", [])
        all_items.extend(items)

        if not data["data"].get("has_more", False):
            break
        page_token = data["data"].get("page_token")

    return all_items
