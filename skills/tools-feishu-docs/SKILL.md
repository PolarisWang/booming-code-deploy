---
name: feishu-docs
description: 读取飞书公开分享文档内容，支持导出 Markdown 和关键词搜索
triggers:
  - feishu.cn
  - larkoffice.com
  - 飞书文档
  - 飞书链接
---

# 飞书文档读取 Skill

当用户提供飞书文档链接，或说"读取/抓取/导出/搜索这个飞书文档"时，执行以下步骤：

1. 从用户消息中提取飞书文档 URL
2. 根据用户意图选择命令：
   - **读取内容**：`python {skill_dir}/feishu_fetch.py <url>`
   - **导出文件**：`python {skill_dir}/feishu_fetch.py <url> --export-md <output.md>`
   - **搜索关键词**：`python {skill_dir}/feishu_fetch.py <url> --search "<keyword>"`
3. 运行命令并将输出内容展示给用户

## 工具位置

所有脚本位于此 skill 目录内：
```
{skill_dir}/feishu_fetch.py
```

## 使用方式

## 文档语言要求

- 对于读取、搜索、导出已有飞书文档：保持原文，不要擅自翻译或改写原始内容。
- 对于由代理新写入的本地 Markdown 或新创建的飞书文档：除非用户明确要求其他语言，标题、摘要、正文、结论和说明默认使用中文。代码、命令、路径、标识符保持原文。

### 读取文档内容

```bash
python {skill_dir}/feishu_fetch.py <url>
```

执行后将文档内容（Markdown 格式）展示给用户。

### 导出为 Markdown 文件

```bash
python {skill_dir}/feishu_fetch.py <url> --export-md <output_file>
```

### 搜索文档内容

```bash
python {skill_dir}/feishu_fetch.py <url> --search "<keyword>"
```

### 调试（查看原始 JSON）

```bash
python {skill_dir}/feishu_fetch.py <url> --json
```

### 写入飞书文档（从本地 Markdown 创建新文档）

```bash
python {skill_dir}/feishu_write.py --title "<文档标题>" <input.md>
```

或从 stdin：

```bash
cat <input.md> | python {skill_dir}/feishu_write.py --title "<文档标题>"
```

成功后输出文档链接：
```
[OK] 已创建飞书文档：https://boomingtech.feishu.cn/docx/...
```

## 前置条件

需要在环境变量或 `.env` 文件中配置飞书 App 凭证：

```
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
```

如未配置，脚本会给出详细提示。

## 支持的 URL 格式

- `https://*.feishu.cn/docx/<token>` — 新版文档
- `https://*.feishu.cn/wiki/<token>` — 知识库
- `https://*.larkoffice.com/docx/<token>` — 海外版

## 依赖安装

首次使用前：

```bash
pip install -r {skill_dir}/requirements.txt
```
