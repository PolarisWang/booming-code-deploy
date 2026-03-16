#!/usr/bin/env python3
"""飞书文档读取 CLI 工具。

用法：
  python feishu_fetch.py <url>                       # 输出 Markdown 到终端
  python feishu_fetch.py <url> --export-md out.md    # 导出到文件
  python feishu_fetch.py <url> --search "关键词"      # 搜索关键词
  python feishu_fetch.py <url> --json                # 输出原始 JSON blocks
"""
import argparse
import json
import sys
import os

# 将 skill 目录加入 Python 路径，使 feishu 包可导入
sys.path.insert(0, os.path.dirname(__file__))

from feishu.parser import parse_url
from feishu.auth import get_token
from feishu.client import fetch_blocks
from feishu.converter import blocks_to_markdown
from feishu.searcher import search


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="读取飞书公开分享文档内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="飞书文档分享链接")
    parser.add_argument("--export-md", metavar="FILE", help="导出为 Markdown 文件")
    parser.add_argument("--search", metavar="KEYWORD", help="在文档中搜索关键词")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON blocks")
    args = parser.parse_args(argv)

    try:
        doc_token, doc_type = parse_url(args.url)
        token = get_token()
        blocks = fetch_blocks(doc_token, doc_type, token)
    except (ValueError, RuntimeError) as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"网络或 API 错误：{e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(blocks, ensure_ascii=False, indent=2))
        return

    if args.search:
        try:
            results = search(blocks, args.search)
        except Exception as e:
            print(f"搜索出错：{e}", file=sys.stderr)
            sys.exit(1)
        if not results:
            print(f"未找到包含「{args.search}」的段落。")
        else:
            print(f"找到 {len(results)} 处匹配：\n")
            for i, r in enumerate(results, 1):
                print(f"--- 匹配 {i} ---")
                print(r)
                print()
        return

    try:
        md = blocks_to_markdown(blocks)
    except Exception as e:
        print(f"转换出错：{e}", file=sys.stderr)
        sys.exit(1)

    if args.export_md:
        try:
            with open(args.export_md, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"已导出到：{args.export_md}")
        except OSError as e:
            print(f"文件写入失败：{e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(md)


if __name__ == "__main__":
    run()
