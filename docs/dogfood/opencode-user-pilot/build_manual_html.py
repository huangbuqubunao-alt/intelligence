#!/usr/bin/env python3
"""Convert USER_MANUAL.md into a standalone, browser-viewable HTML manual."""
import html
import re
import sys
from pathlib import Path

SRC = Path(__file__).parent / "USER_MANUAL.md"
DST = Path(__file__).parent / "USER_MANUAL.html"


def render_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def render_table(lines: list[str]) -> str:
    out = ["<table>"]
    for i, line in enumerate(lines):
        if re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", line) and "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        tag = "th" if i == 0 else "td"
        out.append("<tr>" + "".join(f"<{tag}>{render_inline(c)}</{tag}>" for c in cells) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def convert(md: str) -> str:
    lines = md.splitlines()
    body: list[str] = []
    i = 0
    in_table = False
    table_buf: list[str] = []
    while i < len(lines):
        line = lines[i]
        if line.startswith("|"):
            if not in_table:
                in_table = True
                table_buf = []
            table_buf.append(line)
            i += 1
            continue
        if in_table:
            body.append(render_table(table_buf))
            in_table = False
            table_buf = []
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            body.append(f"<h{level}>{render_inline(m.group(2))}</h{level}>")
        elif line.startswith("!["):
            alt, path = re.match(r"!\[(.*?)\]\((.*?)\)", line).groups()
            body.append(
                f'<figure><img src="{path}" alt="{html.escape(alt)}"/></figure>'
                f"<figcaption>{html.escape(alt)}</figcaption></figure>"
            )
        elif re.match(r"^\s*-\s+", line):
            body.append(f"<li>{render_inline(re.sub(r'^\s*-\s+', '', line))}</li>")
        elif line.strip() == "":
            if body and body[-1].startswith("<li>"):
                body.append("</ul>")
            body.append("")
        else:
            body.append(f"<p>{render_inline(line)}</p>")
        i += 1
    if in_table:
        body.append(render_table(table_buf))
    if body and body[-1].startswith("<li>"):
        body.append("</ul>")
    content = "\n".join(body)
    content = re.sub(r"(<li>.*?</li>\n)(?!<li>)", r"<ul>\1</ul>", content, flags=re.S)
    # ensure the navigation links that were escaped still work
    return content


HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Intelligence 用户使用手册</title>
<style>
:root { color-scheme: light; }
body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; max-width: 880px; margin: 0 auto; padding: 2rem 1.5rem 4rem; line-height: 1.75; color: #1c1e21; background: #fff; }
h1 { font-size: 2rem; border-bottom: 3px solid #0e7a4f; padding-bottom: .5rem; }
h2 { font-size: 1.5rem; margin-top: 2.5rem; border-bottom: 1px solid #ddd; padding-bottom: .3rem; }
h3 { font-size: 1.15rem; margin-top: 1.6rem; color: #0e7a4f; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .95rem; }
th, td { border: 1px solid #d0d4d8; padding: .5rem .7rem; text-align: left; vertical-align: top; }
th { background: #f2f6f4; }
code { background: #f2f2f2; padding: .1rem .35rem; border-radius: 4px; font-size: .9em; }
figure { margin: 1.2rem 0; text-align: center; }
figure img { max-width: 100%; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
figcaption { font-size: .85rem; color: #6b7280; margin-top: .4rem; }
ul { padding-left: 1.4rem; }
li { margin: .25rem 0; }
blockquote { border-left: 4px solid #0e7a4f; margin: 1rem 0; padding: .5rem 1rem; background: #f6faf8; color: #374151; }
strong { color: #0b5e3c; }
a { color: #0e7a4f; }
</style>
</head>
<body>
"""

FOOT = """
<footer style="margin-top:3rem;padding-top:1rem;border-top:1px solid #ddd;color:#6b7280;font-size:.9rem">
<p>Intelligence 用户使用手册 · 简体中文 · 全部截图来自真实运行的产品（隔离测试环境）。</p>
</footer>
</body>
</html>
"""


def main() -> None:
    md = SRC.read_text(encoding="utf-8")
    body = convert(md)
    # fix the escaped table content (render_table re-escapes via render_inline only)
    DST.write_text(HEAD + body + FOOT, encoding="utf-8")
    print(f"written {DST} ({DST.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
