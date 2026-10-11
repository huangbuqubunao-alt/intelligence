#!/usr/bin/env python3
"""Render the unified manual, reusing the preserved OpenCode CSS and table style."""
import html
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = runpy.run_path(str(ROOT.parents[1] / 'dogfood/opencode-user-pilot/build_manual_html.py'))


def inline(value: str) -> str:
    value = html.escape(value)
    value = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', value)
    value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', value)


def render(md: str) -> str:
    out: list[str] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('|'):
            table: list[str] = []
            while i < len(lines) and lines[i].startswith('|'):
                table.append(lines[i])
                i += 1
            out.append(STYLE['render_table'](table))
            continue
        heading = re.match(r'^(#{1,6})\s+(.*)', line)
        picture = re.match(r'!\[(.*?)\]\((.*?)\)', line)
        if heading:
            level, title = len(heading[1]), heading[2]
            slug = re.sub(r'[^\w\s-]', '', title.lower()).replace(' ', '-')
            out.append(f'<h{level} id="{slug}">{inline(title)}</h{level}>')
        elif picture:
            alt, src = picture.groups()
            out.append(f'<figure><img src="{html.escape(src)}" alt="{html.escape(alt)}"/><figcaption>{html.escape(alt)}</figcaption></figure>')
        elif re.match(r'^-\s+', line):
            out.append('<ul>')
            while i < len(lines) and re.match(r'^-\s+', lines[i]):
                out.append(f'<li>{inline(lines[i][2:])}</li>')
                i += 1
            out.append('</ul>')
            continue
        elif line.startswith('> '):
            out.append(f'<blockquote>{inline(line[2:])}</blockquote>')
        elif line == '---':
            out.append('<hr/>')
        elif line.strip():
            out.append(f'<p>{inline(line)}</p>')
        i += 1
    return '\n'.join(out)


if __name__ == '__main__':
    body = render((ROOT / 'USER_MANUAL.md').read_text())
    (ROOT / 'USER_MANUAL.html').write_text(STYLE['HEAD'] + body + STYLE['FOOT'])
