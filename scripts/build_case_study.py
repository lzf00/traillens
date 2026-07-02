"""把 docs/case_study/case_study.md 渲染为可打印 PDF。

流程:
  1. markdown → HTML(纯 Python,不装 markdown 包)
  2. 拼一份带印刷样式的完整 HTML(A4 页面尺寸 + 分页控制)
  3. Playwright chromium headless print_pdf → docs/case_study/traillens.pdf

用途:
  求职/合作时"一键分享"用。~15 页。
"""

from __future__ import annotations
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs/case_study/case_study.md"
OUT_HTML = ROOT / "docs/case_study/traillens.html"
OUT_PDF = ROOT / "docs/case_study/traillens.pdf"


# --------------------------------------------------------------------------- #
# 极简 markdown → HTML(只覆盖本 case study 用到的语法)
# --------------------------------------------------------------------------- #
def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    in_code = False
    in_table = False
    table_align: list[str] = []

    def close_table():
        nonlocal in_table
        if in_table:
            out.append("</tbody></table>")
            in_table = False

    while i < len(lines):
        line = lines[i]

        # code block
        if line.startswith("```"):
            close_table()
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                out.append('<pre class="code"><code>')
                in_code = True
            i += 1
            continue
        if in_code:
            out.append(escape(line))
            i += 1
            continue

        # horizontal rule
        if line.strip() == "---":
            close_table()
            out.append('<hr class="page-break" />')
            i += 1
            continue

        # headers
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_table()
            lvl = len(m.group(1))
            text = inline(m.group(2))
            cls = ""
            if lvl == 1:
                cls = ' class="page-break-before"'
            out.append(f"<h{lvl}{cls}>{text}</h{lvl}>")
            i += 1
            continue

        # table
        if "|" in line and re.match(r"^\s*\|", line):
            close_table()
            # 收集连续表格行
            table_rows = []
            while i < len(lines) and "|" in lines[i] and re.match(r"^\s*\|", lines[i]):
                table_rows.append(lines[i])
                i += 1
            if len(table_rows) >= 2 and re.match(r"^\s*\|[-: |]+\|\s*$", table_rows[1]):
                head = [c.strip() for c in table_rows[0].strip().strip("|").split("|")]
                sep = table_rows[1]
                aligns = []
                for c in sep.strip().strip("|").split("|"):
                    c = c.strip()
                    if c.startswith(":") and c.endswith(":"):
                        aligns.append("center")
                    elif c.endswith(":"):
                        aligns.append("right")
                    else:
                        aligns.append("left")
                body_rows = [
                    [c.strip() for c in r.strip().strip("|").split("|")]
                    for r in table_rows[2:]
                ]
                out.append("<table><thead><tr>")
                for h, a in zip(head, aligns):
                    out.append(f'<th style="text-align:{a}">{inline(h)}</th>')
                out.append("</tr></thead><tbody>")
                for row in body_rows:
                    out.append("<tr>")
                    for c, a in zip(row, aligns):
                        out.append(f'<td style="text-align:{a}">{inline(c)}</td>')
                    out.append("</tr>")
                out.append("</tbody></table>")
            continue

        # list
        m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if m:
            close_table()
            # 简单起见,单级列表
            items = []
            while i < len(lines):
                m2 = re.match(r"^(\s*)[-*]\s+(.*)$", lines[i])
                if not m2:
                    break
                items.append(inline(m2.group(2)))
                i += 1
            out.append("<ul>")
            for it in items:
                out.append(f"<li>{it}</li>")
            out.append("</ul>")
            continue

        # numbered list
        m = re.match(r"^(\s*)\d+\.\s+(.*)$", line)
        if m:
            close_table()
            items = []
            while i < len(lines):
                m2 = re.match(r"^(\s*)\d+\.\s+(.*)$", lines[i])
                if not m2:
                    break
                items.append(inline(m2.group(2)))
                i += 1
            out.append("<ol>")
            for it in items:
                out.append(f"<li>{it}</li>")
            out.append("</ol>")
            continue

        # blank line
        if not line.strip():
            close_table()
            i += 1
            continue

        # blockquote
        if line.startswith("> "):
            close_table()
            out.append(f"<blockquote>{inline(line[2:])}</blockquote>")
            i += 1
            continue

        # paragraph
        close_table()
        out.append(f"<p>{inline(line)}</p>")
        i += 1

    close_table()
    if in_code:
        out.append("</code></pre>")

    return "\n".join(out)


def inline(text: str) -> str:
    """处理 **bold** / *em* / `code` / [text](url) — 不 escape URL 内容前先处理链接。"""
    # 链接 [text](url)
    def link_repl(m):
        return f'<a href="{escape(m.group(2))}">{escape(m.group(1))}</a>'
    text_html = escape(text)
    # 用 raw text 再匹配比较麻烦,退化:先 escape,再从 escaped 里找模式
    text_html = re.sub(r"\[(.+?)\]\((.+?)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text_html)
    text_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text_html)
    text_html = re.sub(r"`(.+?)`", r"<code>\1</code>", text_html)
    return text_html


# --------------------------------------------------------------------------- #
# 页面样式(A4 print 优化)
# --------------------------------------------------------------------------- #
STYLE = """
@page {
  size: A4;
  margin: 20mm 18mm;
}
body {
  font-family: 'Songti SC', 'PingFang SC', 'Fraunces', Georgia, serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #1a1a1a;
  max-width: none;
}
h1 { font-size: 24pt; margin-top: 0; page-break-before: always; border-bottom: 2px solid #333; padding-bottom: 4px; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 15pt; margin-top: 18pt; color: #333; border-left: 3px solid #6FBF8B; padding-left: 8px; }
h3 { font-size: 12pt; margin-top: 14pt; color: #555; }
p { margin: 6pt 0; text-align: justify; }
code { font-family: 'JetBrains Mono', Menlo, Consolas, monospace; font-size: 9pt; background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }
pre.code { font-family: 'JetBrains Mono', Menlo, Consolas, monospace; font-size: 8.5pt; background: #f6f6f6; padding: 10px; border-radius: 4px; overflow-x: auto; line-height: 1.3; page-break-inside: avoid; }
pre.code code { background: transparent; padding: 0; }
table { border-collapse: collapse; margin: 8pt 0; font-size: 9.5pt; width: 100%; page-break-inside: avoid; }
th, td { border: 1px solid #ddd; padding: 4px 8px; }
th { background: #f0f0f0; font-weight: 600; }
blockquote { border-left: 3px solid #ccc; padding-left: 10px; color: #555; margin: 8pt 0; font-style: italic; }
ul, ol { margin: 6pt 0; padding-left: 22pt; }
li { margin: 3pt 0; }
a { color: #4a7bc0; text-decoration: none; }
hr.page-break { display: none; }
h1.page-break-before { page-break-before: always; }
h1:first-of-type.page-break-before { page-break-before: avoid; }
/* 首页样式 */
h1 + h2 { border-left: none; padding-left: 0; text-align: center; font-size: 13pt; color: #666; margin-top: 4pt; }
"""


def main():
    md = MD.read_text(encoding="utf-8")
    body_html = md_to_html(md)
    full_html = f"""<!doctype html>
<html lang="zh"><head>
<meta charset="utf-8">
<title>TrailLens Case Study</title>
<style>{STYLE}</style>
</head><body>
{body_html}
</body></html>
"""
    OUT_HTML.write_text(full_html, encoding="utf-8")
    print(f"HTML: {OUT_HTML} ({OUT_HTML.stat().st_size // 1024}KB)")

    # Playwright print to PDF
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"file://{OUT_HTML}", wait_until="load")
        page.pdf(
            path=str(OUT_PDF),
            format="A4",
            margin={"top": "20mm", "bottom": "20mm", "left": "18mm", "right": "18mm"},
            print_background=True,
        )
        browser.close()
    print(f"PDF:  {OUT_PDF} ({OUT_PDF.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
