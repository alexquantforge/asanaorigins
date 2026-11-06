# -*- coding: utf-8 -*-
"""Shared helpers for turning the source PDFs into site JSON.

Nothing here rewrites the source: text is copied and only split into blocks.
Inline emphasis (bold / italic) is preserved as <strong> / <em> because it
carries meaning in the source (quoted passages, lead-ins, editorial remarks).
"""
import re

import pymupdf

ZWSP = "\u200b"
DASH = "\u2011"


def clean(s: str) -> str:
    s = s.replace(ZWSP, "").replace("\xa0", " ")
    s = s.replace(DASH, "-")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def linkify(text: str) -> str:
    """Escape text and turn bare URLs into links (no other markup)."""
    text = text.replace(ZWSP, "").replace("\u00ad", "").replace(DASH, "-")
    text = re.sub(r"[ \t]{2,}", " ", text)
    parts = re.split(r"(https?://[^\s]+)", text)
    out = []
    for part in parts:
        if part.startswith("http"):
            url = part.rstrip(".,;)»")
            tail = part[len(url):]
            out.append('<a href="%s" target="_blank" rel="noopener nofollow">%s</a>%s'
                       % (esc(url), esc(url), esc(tail)))
        else:
            out.append(esc(part))
    return "".join(out)


def runs_html(runs) -> str:
    """runs: [(text, bold, italic)] -> escaped inline HTML.

    Spacing inside a line is preserved; only the line's outer edges are
    trimmed, so emphasis never glues words together.
    """
    parts = [[t, b, i] for t, b, i in runs if t]
    if not parts:
        return ""
    parts[0][0] = parts[0][0].lstrip()
    parts[-1][0] = parts[-1][0].rstrip()
    out = []
    for text, bold, italic in parts:
        if not text:
            continue
        piece = linkify(text)
        if bold and italic:
            piece = "<strong><em>%s</em></strong>" % piece
        elif bold:
            piece = "<strong>%s</strong>" % piece
        elif italic:
            piece = "<em>%s</em>" % piece
        out.append(piece)
    return "".join(out)


def merge_runs(runs):
    merged = []
    for text, bold, italic in runs:
        if not text:
            continue
        if merged and merged[-1][1] == bold and merged[-1][2] == italic:
            merged[-1][0] += text
        else:
            merged.append([text, bold, italic])
    return [tuple(r) for r in merged]


class Line:
    __slots__ = ("runs", "x0", "y0", "x1", "y1", "page", "size")

    def __init__(self, runs, x0, y0, y1, page, size=0.0, x1=0.0):
        self.runs = runs
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.page = page
        self.size = size

    @property
    def text(self):
        return clean("".join(r[0] for r in self.runs))

    @property
    def bold(self):
        total = sum(len(r[0]) for r in self.runs) or 1
        bold = sum(len(r[0]) for r in self.runs if r[1])
        return bold / total

    @property
    def italic(self):
        total = sum(len(r[0].strip()) for r in self.runs) or 1
        ital = sum(len(r[0].strip()) for r in self.runs if r[2])
        return ital / total


class Block:
    __slots__ = ("lines", "x0", "y0", "y1", "page")

    def __init__(self, lines, page):
        self.lines = lines
        self.page = page
        self.x0 = min(l.x0 for l in lines)
        self.y0 = min(l.y0 for l in lines)
        self.y1 = max(l.y1 for l in lines)

    @property
    def text(self):
        return clean(" ".join(l.text for l in self.lines if l.text))

    @property
    def x1_last(self):
        """Right edge of the last line (a full one continues on the next page)."""
        return self.lines[-1].x1 if self.lines else 0.0

    @property
    def size(self):
        return max((l.size for l in self.lines), default=0)

    @property
    def bold(self):
        total = sum(len(r[0]) for l in self.lines for r in l.runs) or 1
        return sum(len(r[0]) for l in self.lines for r in l.runs if r[1]) / total

    @property
    def italic(self):
        return sum(l.italic for l in self.lines) / max(1, len(self.lines))

    def html(self):
        return " ".join(runs_html(l.runs) for l in self.lines if l.text)


def cell_text(page, rect):
    """Text of a table cell with normal spacing, emphasis dropped."""
    blocks = page.get_text("blocks", clip=pymupdf.Rect(rect))
    parts = []
    for b in sorted(blocks, key=lambda b: (round(b[1], 1), b[0])):
        t = clean(" ".join(b[4].split()))
        if t:
            parts.append(t)
    return " ".join(parts)


def page_items(page):
    """Blocks and tables of a page in reading order, table cells excluded."""
    items = []
    regions = []
    try:
        found = page.find_tables()
    except Exception:  # pragma: no cover - very old pymupdf
        found = None
    if found:
        for table in found.tables:
            rect = pymupdf.Rect(table.bbox)
            regions.append(rect)
            rows = []
            for row in table.rows:
                cells = []
                seen = set()
                for cell in row.cells:
                    if cell is None:
                        cells.append("")
                        continue
                    key = tuple(round(v) for v in cell)
                    if key in seen:
                        cells.append("")
                        continue
                    seen.add(key)
                    cells.append(cell_text(page, cell))
                rows.append(cells)
            rows = [r for r in rows if any(c.strip() for c in r)]
            if rows:
                cols = []
                for cell in table.rows[0].cells:
                    if cell is None:
                        continue
                    x0c, _, x1c, _ = cell
                    if cols and x0c < cols[-1][0] + 4:
                        cols[-1] = (cols[-1][0], max(cols[-1][1], x1c))
                    else:
                        cols.append((x0c, x1c))
                items.append({"kind": "table", "rows": rows, "cols": cols,
                              "y": rect.y0, "x": rect.x0, "page": page.number,
                              "bbox": (rect.x0, rect.y0, rect.x1, rect.y1)})
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        x0, y0, x1, y1 = b["bbox"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if any(r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1 for r in regions):
            continue
        lines = []
        for line in b["lines"]:
            runs = []
            for span in line["spans"]:
                text = span["text"]
                if not text:
                    continue
                runs.append([text, "Bold" in span["font"], "Italic" in span["font"],
                             span["size"]])
            size = max((r[3] for r in runs), default=0)
            runs = merge_runs([(t, b_, i) for t, b_, i, _ in runs])
            if not "".join(r[0] for r in runs).strip():
                continue
            lb = line["bbox"]
            lines.append(Line(runs, lb[0], lb[1], lb[3], page.number,
                              round(size, 1), lb[2]))
        if not lines:
            continue
        items.append({"kind": "block", "block": Block(lines, page.number),
                      "y": lines[0].y0, "x": lines[0].x0, "page": page.number})
    items.sort(key=lambda it: (round(it["y"], 1), it["x"]))
    return items


def assemble_paragraphs(pieces, gap=8.0, join_page_break=True):
    """Group blocks into paragraphs using vertical gaps and indentation.

    pieces: list of Block objects already known to belong to one paragraph run.
    A new paragraph starts when the gap is larger than `gap` or the left
    margin changes; a page break joins only when the previous block looks
    unfinished.
    """
    paras = []
    cur = []
    prev = None
    for blk in pieces:
        if prev is not None:
            same_page = prev.page == blk.page
            gap_ = blk.y0 - prev.y1 if same_page else None
            new_para = True
            if same_page:
                new_para = gap_ is not None and gap_ > gap
                if abs(blk.x0 - prev.x0) > 6:
                    new_para = True
            else:
                tail = prev.text[-1:] if prev.text else ""
                new_para = not (tail and tail not in ".!?:;»”")
                if not join_page_break:
                    new_para = True
            if new_para and cur:
                paras.append(cur)
                cur = []
        cur.append(blk)
        prev = blk
    if cur:
        paras.append(cur)
    return paras


def para_html(blocks):
    return " ".join(b.html() for b in blocks)


BULLET_STEP = 18.0


def split_bullets(block, base=None):
    """Split a block of ●-bullets into `(lead_html, items)`.

    Each item is `{"html": ..., "level": n}`; nested bullets (indented past the
    `base` left margin) get level 2 and so on, as printed in the source.
    """
    groups = []          # [(indent, [runs per line])]
    lead = []
    for line in block.lines:
        text = line.text
        if not text:
            continue
        if text.lstrip(" \t").startswith("●"):
            groups.append([line.x0, [line.runs]])
        elif groups:
            groups[-1][1].append(line.runs)
        else:
            lead.append(line.runs)
    if base is None:
        base = min((g[0] for g in groups), default=block.x0)
    out_items = []
    for indent, runs_list in groups:
        html = " ".join(runs_html(merge_runs([tuple(r) for r in runs]))
                        for runs in runs_list)
        html = re.sub(r"^●\s*", "", html)
        html = re.sub(r"^\s*●\s*", "", html)
        html = re.sub(r"^(<(strong|em)>)\s*", r"\1", html)
        html = re.sub(r"^<(strong|em)>\s*</\1>", "", html)
        level = 1 + max(0, int(round((indent - base) / BULLET_STEP)))
        out_items.append({"html": html.strip(), "level": level})
    lead_html = " ".join(runs_html(merge_runs([tuple(r) for r in runs])) for runs in lead)
    return lead_html.strip(), out_items


def looks_like_list(block):
    return any(l.text.lstrip().startswith("●") for l in block.lines)
