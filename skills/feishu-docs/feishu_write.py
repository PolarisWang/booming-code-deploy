#!/usr/bin/env python3
"""飞书文档写入 CLI 工具。

用法：
  python feishu_write.py --title "文档标题" input.md              # 组织内有链接可读（默认）
  python feishu_write.py --title "标题" --share anyone input.md   # 所有人（含外部）可读
  python feishu_write.py --title "标题" --share closed input.md   # 仅创建者可访问
  cat input.md | python feishu_write.py --title "标题"            # 从 stdin 写入
"""
import argparse
import sys
import os

# 将 skill 目录加入 Python 路径，使 feishu 包可导入
sys.path.insert(0, os.path.dirname(__file__))

from feishu.auth import get_token
from feishu.writer import markdown_to_blocks, create_document, PartialWriteError
from feishu_auth import get_user_token

_SHARE_OPTIONS = {
    "tenant":  "tenant_readable",   # 组织内所有人可读（默认）
    "anyone":  "anyone_readable",   # 所有人可读（含外部）
    "closed":  "closed",            # 关闭链接分享
}


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="将 Markdown 内容写入飞书，创建新文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--title", required=True, help="飞书文档标题（必填）")
    parser.add_argument(
        "--share",
        choices=["tenant", "anyone", "closed"],
        default="tenant",
        help="链接分享权限：tenant=组织内可读（默认），anyone=所有人可读，closed=不分享",
    )
    parser.add_argument(
        "--folder",
        default=None,
        metavar="FOLDER_TOKEN",
        help="目标文件夹 token（不填则读 FEISHU_FOLDER_TOKEN 环境变量；不填时进入机器人空间）",
    )
    parser.add_argument("file", nargs="?", help="输入 Markdown 文件路径（省略时从 stdin 读取）")
    args = parser.parse_args(argv)

    # 读取 Markdown 内容
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                md = f.read()
        except OSError as e:
            print(f"错误：{e}", file=sys.stderr)
            sys.exit(1)
    else:
        if sys.stdin.isatty():
            print("错误：请指定输入文件或通过 stdin 传入内容。\n"
                  "用法：cat input.md | python feishu_write.py --title \"标题\"",
                  file=sys.stderr)
            sys.exit(1)
        md = sys.stdin.read()

    link_share = _SHARE_OPTIONS[args.share]

    # 如果有个人文件夹 token，先通过 OAuth 获取临时 user_access_token
    folder = args.folder or os.environ.get("FEISHU_FOLDER_TOKEN")
    if folder:
        print("需要飞书授权才能上传到个人空间...")
        try:
            user_token = get_user_token(silent=False)
            # 临时注入环境变量（仅当前进程，不写 .env）
            os.environ["FEISHU_USER_ACCESS_TOKEN"] = user_token
        except RuntimeError as e:
            print(f"错误：授权失败 — {e}", file=sys.stderr)
            sys.exit(1)

    # 转换并写入
    try:
        token = get_token()
        blocks = markdown_to_blocks(md)
        url = create_document(args.title, blocks, token,
                              link_share=link_share,
                              folder_token=args.folder)
    except PartialWriteError as e:
        print(f"错误：{e}", file=sys.stderr)
        print(f"[PARTIAL] 文档已创建但内容不完整，可访问：{e.url}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        msg = str(e)
        print(f"错误：{msg}", file=sys.stderr)
        if "99991672" in msg:
            print("提示：需要飞书应用具有 docx:document 写入权限。", file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError) as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"网络或 API 错误：{e}", file=sys.stderr)
        sys.exit(1)

    share_hint = {
        "tenant_readable": "（组织内有链接可读）",
        "anyone_readable": "（所有人有链接可读）",
        "closed": "（仅创建者可访问）",
    }.get(link_share, "")
    print(f"[OK] 已创建飞书文档{share_hint}：{url}")


if __name__ == "__main__":
    run()
