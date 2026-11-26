"""pdf_struct.py -- layout-aware PDF structure extraction (v2).

Contract
--------
Every emitted block carries `page` + `bbox` so any sentence can be traced back to
the page ("核得回").  Text is copied verbatim from the text layer; nothing is
reconstructed by guesswork.  Unrecoverable structure is *flagged*, not invented.

Pipeline per page
-----------------
1. flatten PyMuPDF "dict" output into line records (spans keep size/font/flags)
2. merge same-row fragments ("3.1" + "Attention" -> one heading)
3. detect column bands from short-line projection (gutters)
4. split lines into column buckets + spanning bucket, group each into
   paragraphs with geometric break rules (never across a gutter)
5. classify blocks (title/heading/body/formula/caption/footnote/margin)
6. attach tables (PyMuPDF table finder) and figures (raster + caption anchors)
7. order blocks with band segmentation: spanning blocks cut the page into bands,
   inside a band columns are consumed left-to-right, top-to-bottom

Only PyMuPDF is required (>=1.23).
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import sys

try:  # PyMuPDF >= 1.24 exposes the canonical name
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore

SCHEMA = "pdf-struct/2"

# --------------------------------------------------------------------------- #
# character classes
# --------------------------------------------------------------------------- #
MATH_CHARS = set(
    "=+-−×÷·∙∗±∓≤≥≦≧≠≈≡∼∝∞∂∇∑∏∫∬√∛∈∉⊂⊃⊆⊇∪∩∀∃¬∧∨→←↔⇒⇔⊕⊗∅ℝℕℤℓ"
    "αβγδεζηθικλμνξοπρστυφχψω"
    "ΓΔΘΛΞΠΣΦΨΩ"
    "⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉"
)
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
PAGENUM_RE = re.compile(r"^[\s\-–—]*(\d{1,4}|[ivxlcdm]{1,7})[\s\-–—]*$", re.I)
NUM_HEAD_RE = re.compile(r"^(?P<num>\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+(?P<rest>\S.{0,90})$")
CN_HEAD_RE = re.compile(
    r"^(?P<num>[一二三四五六七八九十]{1,3}\s*[、.．]|第[一二三四五六七八九十百]{1,3}[章节篇条]"
    r"|（[一二三四五六七八九十]{1,3}）)\s*(?P<rest>.{0,90})$")
REF_HEAD_RE = re.compile(
    r"^(?:\d{1,2}\.?\s*)?(references?|bibliography|works cited|参考文献|引用文献)\s*$", re.I)
CAPTION_RE = re.compile(
    r"^\s*(figure|fig\.?|table|tab\.?|algorithm|scheme|图|表|插图|续表)\s*"
    r"([A-Z]?\.?\d+|[IVX]+)[\s:：.．]", re.I)
FIG_CAP_RE = re.compile(
    r"^\s*(?:figure|fig\.?|图|插图)\s*([A-Z]?\.?\d+|[IVX]+)[\s:：.．]", re.I)
# same label, but allowed to start mid-block: figure labels often glue themselves
# onto the caption paragraph (axis labels, legends)
FIG_CAP_ANY_RE = re.compile(
    r"(?:^|[\s.。)\]])?(?:figure|fig\.?|图|插图)\s*([A-Z]?\.?\d+|[IVX]+)[\s:：.．]", re.I)


def is_cjk(ch: str) -> bool:
    return bool(ch and CJK_RE.match(ch))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def r2(v) -> float:
    return round(float(v), 2)


def _mupdf_version() -> str:
    """PyMuPDF's __version__ is the binding version; the MuPDF library version
    lives in __doc__ ("PyMuPDF 2.1: ... MuPDF 1.28.6 library.")."""
    m = re.search(r"(?<!Py)MuPDF ([\d.]+)", getattr(fitz, "__doc__", "") or "")
    return m.group(1) if m else ""


def nospace_len(s: str) -> int:
    return len(re.sub(r"\s+", "", s or ""))


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #
def union_bbox(boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return [r2(min(b[0] for b in boxes)), r2(min(b[1] for b in boxes)),
            r2(max(b[2] for b in boxes)), r2(max(b[3] for b in boxes))]


def line_h(l):
    return max(1.0, l["bbox"][3] - l["bbox"][1])


# --------------------------------------------------------------------------- #
# 1. flatten
# --------------------------------------------------------------------------- #
def page_lines(page):
    flags = fitz.TEXTFLAGS_TEXT | getattr(fitz, "TEXT_PRESERVE_WHITESPACE", 0)
    raw = page.get_text("dict", flags=flags)
    lines, images = [], []
    for bi, blk in enumerate(raw.get("blocks", [])):
        if blk.get("type", 0) == 1:
            images.append({"bbox": [r2(v) for v in blk["bbox"]],
                           "width": blk.get("width"), "height": blk.get("height")})
            continue
        for li, ln in enumerate(blk.get("lines", [])):
            spans = []
            for sp in ln.get("spans", []):
                txt = sp.get("text", "")
                if not txt:
                    continue
                fl = int(sp.get("flags", 0))
                spans.append({
                    "text": txt, "bbox": [r2(v) for v in sp["bbox"]],
                    "size": round(float(sp.get("size", 0)), 2),
                    "font": sp.get("font", ""), "flags": fl,
                    "sup": bool(fl & 1), "italic": bool(fl & 2),
                    "bold": bool(fl & 16), "mono": bool(fl & 8),
                })
            if not spans:
                continue
            text = "".join(s["text"] for s in spans)
            if not text.strip():
                continue
            dx, dy = ln.get("dir", (1, 0))
            lines.append({
                "raw_block_index": bi, "raw_line_index": li,
                "bbox": [r2(v) for v in ln["bbox"]],
                "dir": [round(dx, 3), round(dy, 3)],
                "rotated": abs(dy) > 0.05 or dx < 0.9,
                "spans": spans, "text": text,
                "size": max(s["size"] for s in spans),
                "bold": any(s["bold"] for s in spans),
                "italic": any(s["italic"] for s in spans),
                "mono": all(s["mono"] for s in spans),
                "font": _mode([s["font"] for s in spans]),
            })
    return lines, images


def _mode(seq):
    d = {}
    for x in seq:
        d[x] = d.get(x, 0) + 1
    return max(d.items(), key=lambda kv: kv[1])[0] if d else ""


# --------------------------------------------------------------------------- #
# 2. same-row fragment merge ("3.1" + "Attention")
# --------------------------------------------------------------------------- #
def merge_rows(lines, max_gap=14.0):
    rows = {}
    for l in lines:
        key = round((l["bbox"][1] + l["bbox"][3]) / 2.0 / 1.5)
        rows.setdefault(key, []).append(l)
    out = []
    for key in sorted(rows):
        group = sorted(rows[key], key=lambda l: l["bbox"][0])
        cur = group[0]
        for nl in group[1:]:
            gap = nl["bbox"][0] - cur["bbox"][2]
            same_style = abs(nl["size"] - cur["size"]) <= 0.6 and nl["bold"] == cur["bold"]
            if same_style and -1.0 <= gap <= max_gap:
                cur = {
                    "bbox": union_bbox([cur["bbox"], nl["bbox"]]),
                    "dir": cur["dir"], "rotated": cur["rotated"],
                    "spans": cur["spans"] + nl["spans"],
                    "text": cur["text"].rstrip() + (" " if gap > 0.8 else "") + nl["text"].lstrip(),
                    "size": max(cur["size"], nl["size"]),
                    "bold": cur["bold"] or nl["bold"],
                    "italic": cur["italic"] or nl["italic"],
                    "mono": cur["mono"] and nl["mono"],
                    "font": cur["font"] or nl["font"],
                    "raw_block_index": cur["raw_block_index"],
                    "raw_line_index": cur["raw_line_index"],
                }
            else:
                out.append(cur)
                cur = nl
        out.append(cur)
    return out


# --------------------------------------------------------------------------- #
# 3. columns
# --------------------------------------------------------------------------- #
def detect_columns(lines, page_w):
    """Return (column_ranges, gutters).  Only *short* lines vote so that a
    full-width title cannot mask the gutter of a two-column page."""
    if len(lines) < 10:
        return [(0.0, float(page_w))], []
    xs0 = min(l["bbox"][0] for l in lines)
    xs1 = max(l["bbox"][2] for l in lines)
    content_w = max(1.0, xs1 - xs0)
    short = [l for l in lines if (l["bbox"][2] - l["bbox"][0]) < 0.62 * content_w]
    voters = short if len(short) >= 10 else [l for l in lines if not l["rotated"]]
    W = int(math.ceil(page_w)) + 2
    cov = [0] * W
    for l in voters:
        a = max(0, int(math.floor(l["bbox"][0])))
        b = min(W - 1, int(math.ceil(l["bbox"][2])))
        for x in range(a, b + 1):
            cov[x] += 1
    lo, hi = max(0, int(math.floor(xs0))), min(W - 1, int(math.ceil(xs1)))
    # A gutter is a strip no *body* line covers.  Tolerate a single intruding
    # line (equation number, page number, footnote mark) because otherwise one
    # stray "(2)" in the margin destroys the split; two or more lines never do.
    runs, start = [], None
    for x in range(lo, hi + 1):
        if cov[x] <= 1:
            if start is None:
                start = x
        elif start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, hi))
    gutters = []
    for a, b in runs:
        if b - a + 1 < 6:
            continue
        mid = (a + b) / 2.0
        left = sum(1 for l in voters if l["bbox"][2] <= mid)
        right = sum(1 for l in voters if l["bbox"][0] >= mid)
        if left >= max(3, 0.15 * len(voters)) and right >= max(3, 0.15 * len(voters)):
            gutters.append((float(a), float(b)))
    if not gutters:
        return [(float(xs0), float(xs1))], []
    gutters.sort()
    merged = [list(gutters[0])]
    for a, b in gutters[1:]:
        if a - merged[-1][1] < 0.10 * content_w:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    cols, cur = [], float(xs0)
    for a, b in merged:
        cols.append((cur, a))
        cur = b
    cols.append((cur, float(xs1)))
    cols = [(c0, c1) for c0, c1 in cols if c1 - c0 > 0.10 * content_w]
    return cols, [tuple(m) for m in merged]


def crosses_gutter(bbox, gutters, tol=1.0):
    for g0, g1 in gutters:
        if bbox[0] < g1 - tol and bbox[2] > g0 + tol:
            return True
    return False


def column_of(bbox, cols, tol=1.5):
    best, best_ov = -1, -1.0
    for i, (c0, c1) in enumerate(cols):
        ov = min(bbox[2], c1) - max(bbox[0], c0)
        if ov > best_ov:
            best, best_ov = i, ov
    return best if best_ov > tol else -1


# --------------------------------------------------------------------------- #
# 4. paragraph grouping inside one column bucket
# --------------------------------------------------------------------------- #
def group_lines(seq, headcheck=None):
    if not seq:
        return []
    seq = sorted(seq, key=lambda l: (l["bbox"][1], l["bbox"][0]))
    blocks, cur = [], [seq[0]]
    for ln in seq[1:]:
        prev = cur[-1]
        pv, cv = prev["bbox"], ln["bbox"]
        gap = cv[1] - pv[3]
        h = min(line_h(prev), line_h(ln))
        ovl = min(pv[2], cv[2]) - max(pv[0], cv[0])
        width = max(1.0, min(pv[2] - pv[0], cv[2] - cv[0]))
        # a heading is a paragraph of its own: never glue it to neighbours
        head_split = bool(headcheck) and (
            headcheck(prev) or headcheck(ln) or any(headcheck(x) for x in cur[:-1]))
        joinable = (
            abs(gap) <= 0 or gap <= 1.6 * h
        ) and gap >= -0.8 * h and ovl >= 0.30 * width \
            and abs(ln["size"] - prev["size"]) <= max(0.8, 0.18 * prev["size"]) \
            and ln["mono"] == prev["mono"] and ln["bold"] == prev["bold"] \
            and not head_split
        if not joinable:
            blocks.append(cur)
            cur = [ln]
            continue
        right_edge = max(l["bbox"][2] for l in cur)
        left_edge = min(l["bbox"][0] for l in cur)
        short_prev = pv[2] < right_edge - max(6.0, 1.15 * h)   # paragraph's last line
        indent = cv[0] > left_edge + max(4.0, 0.9 * h)          # first-line indent
        if short_prev or (indent and pv[2] > right_edge - max(6.0, 1.15 * h)):
            blocks.append(cur)
            cur = [ln]
            continue
        cur.append(ln)
    blocks.append(cur)
    return blocks


# --------------------------------------------------------------------------- #
# 5. classification
# --------------------------------------------------------------------------- #
def join_lines(lines):
    out = ""
    for i, l in enumerate(lines):
        t = l["text"].strip()
        if i == 0:
            out = t
            continue
        if not t:
            continue
        prev_ch = out[-1] if out else ""
        if prev_ch in "-‐" and t[:1].islower():
            out = out[:-1] + t            # end-of-line hyphenation
        elif is_cjk(prev_ch) or is_cjk(t[:1]):
            out = out + t                  # CJK: no space at line break
        else:
            out = out + " " + t
    return out


def sup_sub_text(lines):
    parts = []
    for l in lines:
        for s in l["spans"]:
            parts.append(("^" + s["text"]) if s["sup"] else s["text"])
        parts.append("\n")
    return "".join(parts).rstrip("\n")


def math_density(text):
    t = re.sub(r"\s+", "", text)
    if not t:
        return 0.0, 0
    m = sum(1 for c in t if c in MATH_CHARS)
    return m / len(t), m


def looks_like_heading_line(text, size, bold, body_size):
    """Cheap per-line test used to cut paragraph groups around headings."""
    t = text.strip()
    if not t or len(t) > 90:
        return False
    if REF_HEAD_RE.match(t):
        return True
    if NUM_HEAD_RE.match(t) or CN_HEAD_RE.match(t):
        if t.endswith((".", "。", ",", "，")) and not bold:
            return False
        return size >= body_size * 0.98 or bold
    if size >= body_size * 1.06 and len(t) <= 70 and not t.endswith("."):
        return True
    return False


def classify(text, size, body_size, bold, mono, n_lines):
    t = text.strip()
    if not t:
        return "empty"
    if mono:
        return "code"
    if ARXIV_RE.match(t) and len(t) < 80:
        return "margin_artifact"
    if LICENSE_RE.search(t) and len(t) < 400:
        return "margin_artifact"
    if REF_HEAD_RE.match(t):
        return "heading"
    dens, mcount = math_density(t)
    if n_lines <= 4 and mcount >= 2 and dens >= 0.12 and not CJK_RE.search(t):
        return "formula"
    if CAPTION_RE.match(t) and len(t) < 400:
        return "caption"
    # a sentence fragment ending in a full stop is prose, even when it is set
    # large: licence boilerplate often is
    if len(t) < 40 and t.endswith("."):
        return "body"
    # numbered section headings are often set at body size (e.g. "3.1 Encoder
    # and Decoder Stacks"), so size alone cannot decide; require the number,
    # a Title-cased (or CJK) rest, no sentence-final punctuation and bold/size
    m = NUM_HEAD_RE.match(t) or CN_HEAD_RE.match(t)
    # some house styles (ICLR/NeurIPS camera-ready) set numbered subsections in
    # ALL CAPS at body size and without bold ("3.1 VISION TRANSFORMER (VIT)").
    # Size and weight alone miss those; the number plus an all-caps rest is the
    # evidence.  Guards keep numbered list items and bibliography entries out.
    caps = False
    if m:
        rest0 = (m.groupdict().get("rest") or "").strip()
        caps = bool(rest0) and not re.search(r"[a-z]", rest0) \
            and bool(re.search(r"[A-Z]", rest0)) and len(rest0) >= 4 \
            and n_lines <= 2 \
            and len(t) <= 70 and not re.search(r"\d{4}|et al|[,;]", rest0)
    if m and len(t) <= 90 and (bold or size >= body_size * 1.02 or caps):
        rest = (m.groupdict().get("rest") or "").strip()
        # "3.57 Table 5. Error rates ... The top-5 error" is a sentence, not a
        # heading: a lowercase letter followed by ". " inside the rest means
        # the line already contains a sentence boundary
        if re.search(r"[a-z]\.\s", rest):
            return "body"
        if rest[:1].isupper() or CJK_RE.match(rest[:1] or " "):
            if not (t.endswith((".", "。")) and not bold):
                return "heading"
    if len(t) <= 120 and size >= body_size * 1.06 and (bold or size >= body_size * 1.14):
        return "heading"
    if size >= body_size * 1.35 and len(t) <= 300:
        return "title"
    if size <= body_size * 0.82:
        return "footnote"
    return "body"


def heading_level(block, sizes):
    t = block["text"].strip()
    if REF_HEAD_RE.match(t) or ABSTRACT_RE.match(t) or \
            re.match(r"^(appendix|acknowledg|附录|致谢|参考文献)", t, re.I) or \
            re.match(r"^[A-Z]\.\s+\S", t):
        return 1
    m = NUM_HEAD_RE.match(t)
    if m:
        num = m.group("num")
        return min(4, len(num.split("."))) if "." in num else 1
    m = CN_HEAD_RE.match(t)
    if m:
        return 1
    try:
        return min(4, sorted(sizes, reverse=True).index(round(block["size"], 1)) + 1)
    except ValueError:
        return 3


# --------------------------------------------------------------------------- #
# 6. tables / figures
# --------------------------------------------------------------------------- #
def _cell_text_from_words(words, bbox, pad=0.6):
    """Text of one table cell, rebuilt from word boxes.

    `Table.extract()` interleaves the spans of multi-line cells ("3 3xx3 6 64"),
    so cells are re-read from the word grid: words inside the cell sorted by
    row then x, one line per visual row.  Word order inside a cell is therefore
    the reading order of the cell, and nothing is silently dropped.
    """
    x0, y0, x1, y1 = bbox
    sel = []
    for w in words:
        cx = (w[0] + w[2]) / 2.0
        cy = (w[1] + w[3]) / 2.0
        if x0 - pad <= cx <= x1 + pad and y0 - pad <= cy <= y1 + pad:
            sel.append(w)
    if not sel:
        return ""
    sel.sort(key=lambda w: (round(w[1] / 3.0), w[0]))
    lines, cur, cury = [], [], None
    for w in sel:
        if cury is None or abs(w[1] - cury) <= 2.2:
            cur.append(w)
            if cury is None:
                cury = w[1]
        else:
            lines.append(cur)
            cur, cury = [w], w[1]
    if cur:
        lines.append(cur)
    return "\n".join(" ".join(x[4] for x in ln) for ln in lines)


def find_tables(page, log=None):
    out = []
    try:
        tf = page.find_tables()
    except Exception as exc:
        if log:
            log("  [warn] find_tables failed on page %d: %s" % (page.number + 1, exc))
        return out
    for t in (getattr(tf, "tables", []) or []):
        try:
            data = t.extract()
        except Exception:
            continue
        rows = [["" if c is None else str(c).strip() for c in row] for row in data]
        if not rows:
            continue
        ncol = max(len(r) for r in rows)
        rows = [r + [""] * (ncol - len(r)) for r in rows]
        filled = sum(1 for r in rows for c in r if c)
        header, body = [], []
        try:
            header = [str(x).strip() if x is not None else "" for x in t.header.names]
        except Exception:
            header = rows[0] if rows else []
        body = rows[1:] if len(rows) > 1 else []
        # rebuild every cell from the word grid; keep extract() only as fallback
        try:
            words = page.get_text("words")
        except Exception:
            words = []
        bbox_cells = [{"row": ri, "col": ci,
                       "bbox": [r2(v) for v in (cc or (0, 0, 0, 0))]}
                      for ri, r in enumerate(t.rows)
                      for ci, cc in enumerate(r.cells)]
        if words and bbox_cells:
            grid = [["" for _ in range(ncol)] for _ in rows]
            for c in bbox_cells:
                ri, ci = c["row"], c["col"]
                if ri >= len(grid) or ci >= ncol:
                    continue
                txt = _cell_text_from_words(words, c["bbox"])
                if txt:
                    grid[ri][ci] = txt
            # keep extract() text where the word grid produced nothing
            for ri in range(len(grid)):
                for ci in range(ncol):
                    if not grid[ri][ci] and ri < len(rows) and ci < len(rows[ri]):
                        grid[ri][ci] = rows[ri][ci]
            rows = grid
            filled = sum(1 for r in rows for c in r if c)
            if not any(header):
                header = rows[0] if rows else []
            body = rows[1:] if len(rows) > 1 else []
        out.append({
            "bbox": [r2(v) for v in t.bbox],
            "n_rows": len(rows), "n_cols": ncol,
            "header": header, "rows": rows, "body_rows": body,
            "cells": [{"row": ri, "col": ci, "text": c}
                      for ri, r in enumerate(rows) for ci, c in enumerate(r)],
            "bbox_cells": bbox_cells,
            "fill_rate": round(filled / max(1, len(rows) * ncol), 3),
            "method": "pymupdf_find_tables",
        })
    return out


def table_to_text(t):
    return "\n".join(" | ".join(r) for r in t.get("rows") or [])


def caption_near(bbox, blocks, kinds=("caption",), max_gap=60.0):
    best, bestd = None, 1e9
    for b in blocks:
        if b["type"] not in kinds:
            continue
        bb = b["bbox"]
        if min(bb[2], bbox[2]) - max(bb[0], bbox[0]) >= -8:
            d = min(abs(bb[1] - bbox[3]), abs(bbox[1] - bb[3]))
            if d < max_gap and d < bestd:
                best, bestd = b["text"], d
    return best


def artwork_near(page, bbox, max_gap=30.0, min_overlap=0.25):
    """Return the bbox of the artwork (raster image or vector cluster) that
    *touches* `bbox`, else None.  A caption must sit against its artwork --
    a body sentence that merely starts with 'Fig. 4.' does not."""
    x0, y0, x1, y1 = bbox
    w = max(1.0, x1 - x0)
    best, bestd = None, 1e9

    def consider(b, gap):
        nonlocal best, bestd
        if gap <= max_gap and gap < bestd:
            ov = min(x1, b[2]) - max(x0, b[0])
            # overlap is measured against the narrower of caption / artwork so a
            # wide caption over a narrow diagram still counts as attached
            if ov >= min_overlap * min(w, max(1.0, b[2] - b[0])):
                best, bestd = b, gap

    for info in page.get_image_info():
        b = [info["bbox"][0], info["bbox"][1], info["bbox"][2], info["bbox"][3]]
        consider(b, max(b[1] - y1, y0 - b[3]))
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []
    boxes = []
    for d in drawings:
        r = d.get("rect")
        if r is None or r.width < 1 or r.height < 1:
            continue
        boxes.append([r.x0, r.y0, r.x1, r.y1])
    # cluster drawings that touch each other so one curve is not "the figure"
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if (min(a[2], b[2]) - max(a[0], b[0]) >= -6 and
                        min(a[3], b[3]) - max(a[1], b[1]) >= -6):
                    boxes[i] = union_bbox([a, b])
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    for b in boxes:
        if b[2] - b[0] < 24 or b[3] - b[1] < 18:
            continue  # rule lines, underlines, table borders
        consider(b, max(b[1] - y1, y0 - b[3]))
    return best


def drawing_bbox_in_window(page, win):
    """Union of vector-drawing rects intersecting `win` (fitz.Rect)."""
    try:
        drawings = page.get_drawings()
    except Exception:
        return None
    boxes = []
    for d in drawings:
        r = d.get("rect")
        if r is None:
            continue
        if r.width < 2 or r.height < 2:
            continue
        if r.intersects(win):
            boxes.append([r.x0, r.y0, r.x1, r.y1])
    if not boxes:
        return None
    return union_bbox(boxes)


# --------------------------------------------------------------------------- #
# 7. reading order
# --------------------------------------------------------------------------- #
def order_blocks(blocks, cols, gutters):
    if not blocks:
        return []
    def spanning(b):
        if len(cols) <= 1:
            return True
        return crosses_gutter(b["bbox"], gutters)
    span = sorted([b for b in blocks if spanning(b)], key=lambda b: (b["bbox"][1], b["bbox"][0]))
    colblocks = [b for b in blocks if not spanning(b)]
    bounds = [-1e9] + [b["bbox"][1] for b in span] + [1e9]
    ordered = []
    for bi in range(len(bounds) - 1):
        top, bot = bounds[bi], bounds[bi + 1]
        band = [b for b in colblocks if top - 0.5 <= b["bbox"][1] < bot - 0.5]
        bycol = {}
        for b in band:
            bycol.setdefault(b["column"], []).append(b)
        for c in sorted(bycol):
            ordered.extend(sorted(bycol[c], key=lambda b: (b["bbox"][1], b["bbox"][0])))
        if bi < len(span):
            ordered.append(span[bi])
    placed = set(id(b) for b in ordered)
    rest = sorted([b for b in blocks if id(b) not in placed],
                  key=lambda b: (b["bbox"][1], b["bbox"][0]))
    ordered.extend(rest)
    return ordered


# --------------------------------------------------------------------------- #
# 8. document
# --------------------------------------------------------------------------- #
def estimate_body_size(lines):
    d = {}
    for l in lines:
        d[round(l["size"], 1)] = d.get(round(l["size"], 1), 0) + nospace_len(l["text"])
    return max(d.items(), key=lambda kv: kv[1])[0] if d else 10.0


def parse_document(path, max_pages=None, dpi=110, log=print):
    doc = fitz.open(path)
    n_pages = doc.page_count
    pages = range(n_pages) if max_pages is None else range(min(n_pages, max_pages))

    # ---- pass 1: lines + column template --------------------------------- #
    per_page = {}
    for pno in pages:
        page = doc[pno]
        lines, images = page_lines(page)
        lines = merge_rows(lines)
        cols, gut = detect_columns([l for l in lines if not l["rotated"]], page.rect.width)
        per_page[pno] = {"w": page.rect.width, "h": page.rect.height,
                         "lines": lines, "images": images, "cols": cols, "gutters": gut}
    votes = [len(p["cols"]) for p in per_page.values() if len(p["lines"]) > 25]
    doc_cols = max(set(votes), key=votes.count) if votes else 1

    # A page whose own votes were too few (dense figure/table page) inherits the
    # document gutter instead of silently collapsing to one column.
    if doc_cols >= 2:
        gs = [g for p in per_page.values() for g in p["gutters"]]
        if gs:
            mids = sorted((a + b) / 2.0 for a, b in gs)
            widths = sorted(b - a for a, b in gs)
            gmid = mids[len(mids) // 2]
            gw = widths[len(widths) // 2]
            for pno, pg in per_page.items():
                if len(pg["cols"]) != 1 or len(pg["lines"]) <= 25:
                    continue
                up = [l for l in pg["lines"] if not l["rotated"]]
                if not up:
                    continue
                xs0 = min(l["bbox"][0] for l in up)
                xs1 = max(l["bbox"][2] for l in up)
                a, b = gmid - gw / 2.0, gmid + gw / 2.0
                if xs1 - xs0 < 3 * gw:
                    continue
                pg["cols"] = [(float(xs0), float(a)), (float(b), float(xs1))]
                pg["gutters"] = [(float(a), float(b))]
                pg["cols_derived"] = "document_template"

    # ---- pass 2: running heads / feet ------------------------------------ #
    band = 0.075
    counter = {}
    for pno, pg in per_page.items():
        for l in pg["lines"]:
            y0, y1 = l["bbox"][1], l["bbox"][3]
            if y1 <= pg["h"] * band or y0 >= pg["h"] * (1 - band):
                counter.setdefault(_norm(l["text"]), set()).add(pno)
    n_eff = max(1, len(per_page))
    running = {k for k, v in counter.items()
               if len(v) >= max(3, int(0.30 * n_eff)) and len(k) >= 3}

    out_pages, all_blocks, warnings, headings = [], [], [], []
    tables, figures = [], []

    for pno in pages:
        pg = per_page[pno]
        W, H, lines = pg["w"], pg["h"], pg["lines"]
        base = {"page": pno + 1, "width": r2(W), "height": r2(H)}
        if not lines:
            out_pages.append({**base, "columns": 0, "gutters": [], "empty": True,
                              "text_layer_chars": 0, "n_blocks": 0, "n_lines": 0})
            warnings.append({"code": "page_without_text_layer", "page": pno + 1,
                             "detail": "no extractable characters; scanned or image-only "
                                       "page -> OCR/vision path required"})
            continue

        text_layer = sum(nospace_len(l["text"]) for l in lines)
        body_lines, dropped = [], []
        for l in lines:
            y0, y1 = l["bbox"][1], l["bbox"][3]
            in_band = y1 <= H * band or y0 >= H * (1 - band)
            if in_band and (_norm(l["text"]) in running or PAGENUM_RE.match(l["text"])):
                dropped.append(l["text"].strip())
                continue
            body_lines.append(l)

        # split buckets
        rot = [l for l in body_lines if l["rotated"]]
        upright = [l for l in body_lines if not l["rotated"]]
        span_lines = [l for l in upright if crosses_gutter(l["bbox"], pg["gutters"])]
        col_lines = [l for l in upright if not crosses_gutter(l["bbox"], pg["gutters"])]
        col_buckets = {}
        for l in col_lines:
            col_buckets.setdefault(column_of(l["bbox"], pg["cols"]), []).append(l)

        body_size = estimate_body_size(upright) if upright else 10.0

        def headcheck(l):
            return looks_like_heading_line(l["text"], l["size"], l["bold"], body_size)

        blocks = []
        for col, seq in sorted(col_buckets.items()):
            for grp in group_lines(seq, headcheck):
                blocks.append(_make_block(grp, pno, col, body_size))
        for grp in group_lines(span_lines, headcheck):
            blocks.append(_make_block(grp, pno, -1, body_size))
        for l in rot:
            blocks.append(_make_block([l], pno, -1, body_size, force_type="margin_artifact"))

        # tables: the grid from find_tables owns its region.  Text lines that
        # live inside the region but are not represented in the grid are kept
        # as extra rows (`unassigned_lines`), so nothing is ever lost and
        # nothing is emitted twice.
        page_tables = find_tables(doc[pno], log=log)
        for t in page_tables:
            t["page"] = pno + 1
            tb = t["bbox"]
            plausible = (t["n_rows"] >= 2 and t["n_cols"] >= 2
                         and t["fill_rate"] >= 0.40
                         and len(re.sub(r"\s+", "", table_to_text(t))) >= 8)
            if not plausible:
                t["rejected"] = "implausible_grid"
                tables.append(t)
                continue
            t["id"] = "T%d" % (len([x for x in tables if not x.get("rejected")]) + 1)
            cap = caption_near(tb, blocks)
            if cap:
                t["caption"] = cap
            region = []
            for b in blocks:
                if b["type"] in ("table", "figure", "caption"):
                    continue
                cx = (b["bbox"][0] + b["bbox"][2]) / 2.0
                cy = (b["bbox"][1] + b["bbox"][3]) / 2.0
                if tb[0] - 2 <= cx <= tb[2] + 2 and tb[1] - 2 <= cy <= tb[3] + 2:
                    region.append(b)
            ttext = re.sub(r"\s+", "", table_to_text(t))
            extra = [b["text"] for b in region
                     if re.sub(r"\s+", "", b["text"]) and
                     _char_overlap(re.sub(r"\s+", "", b["text"]), ttext) < 0.85]
            if extra:
                t["unassigned_lines"] = extra
                t["n_unassigned"] = len(extra)
            t["absorbed_blocks"] = len(region)
            tables.append(t)
            blocks[:] = [b for b in blocks if b not in region]
            tbody = table_to_text(t)
            if extra:
                tbody += "\n" + "\n".join(" | " + x for x in extra)
            blocks.append({"page": pno + 1, "bbox": tb, "column": -1,
                           "type": "table", "text": tbody, "raw": "",
                           "n_lines": t["n_rows"], "size": body_size, "bold": False,
                           "italic": False, "mono": False, "font": "", "sup_sub": None,
                           "table_id": t["id"], "rotated": False})

        # figures: raster blocks, then caption anchors for vector artwork
        for im in pg["images"]:
            bb = im["bbox"]
            if bb[2] - bb[0] < 18 or bb[3] - bb[1] < 18:
                continue
            cap = caption_near(bb, blocks)
            fig = {"id": "F%d" % (len(figures) + 1), "page": pno + 1, "bbox": bb,
                   "caption": cap, "width": im.get("width"), "height": im.get("height"),
                   "artwork": "raster"}
            figures.append(fig)
            blocks.append({"page": pno + 1, "bbox": bb, "column": -1, "type": "figure",
                           "text": "", "raw": "", "n_lines": 0,
                           "size": body_size, "bold": False, "italic": False, "mono": False,
                           "font": "", "sup_sub": None, "figure_id": fig["id"],
                           "rotated": False})
        for b in [x for x in blocks if FIG_CAP_ANY_RE.search(x["text"][:160])
                  and x["type"] not in ("table", "figure")]:
            if any((f["page"] == pno + 1 and _iou(b["bbox"], f["bbox"]) > 0.2) or
                   (f["page"] == pno + 1 and f.get("caption") == b["text"]) for f in figures):
                continue
            art = artwork_near(doc[pno], b["bbox"])
            if art is None:
                # a long prose sentence that merely mentions "Fig. 4." is body
                if len(b["text"]) > 300 and b["type"] == "caption":
                    b["type"] = "body"
                continue
            m = FIG_CAP_ANY_RE.search(b["text"][:160])
            if m and m.start() > 0:
                # drop glued-on figure labels ("relu", "weight layer") that were
                # merged into the caption line; they live inside the artwork
                b["text"] = b["text"][m.start():].strip()
                if b.get("raw"):
                    b["raw"] = b["raw"][b["raw"].find(b["text"][:12]):]
            b["type"] = "caption"
            bb = union_bbox([b["bbox"], art])
            fig = {"id": "F%d" % (len(figures) + 1), "page": pno + 1, "bbox": bb,
                   "caption": b["text"], "artwork": "vector",
                   "width": None, "height": None}
            figures.append(fig)
            blocks.append({"page": pno + 1, "bbox": bb, "column": -1, "type": "figure",
                           "text": "", "raw": "", "n_lines": 0, "size": body_size,
                           "bold": False, "italic": False, "mono": False, "font": "",
                           "sup_sub": None, "figure_id": fig["id"], "rotated": False})

        # Text that lives *inside* artwork (axis ticks, legends, "weight layer")
        # is figure content, not document text: mask it so it never reaches the
        # body flow.  Only label-sized runs are masked, so real paragraphs that
        # merely overlap a loosely drawn figure box survive.
        page_fig_boxes = [f["bbox"] for f in figures if f["page"] == pno + 1]
        for info in doc[pno].get_image_info():
            page_fig_boxes.append([info["bbox"][0], info["bbox"][1],
                                   info["bbox"][2], info["bbox"][3]])
        try:
            for d in doc[pno].get_drawings():
                r = d.get("rect")
                if r is not None and r.width >= 6 and r.height >= 4:
                    page_fig_boxes.append([r.x0, r.y0, r.x1, r.y1])
        except Exception:
            pass
        KEEP = ("table", "figure", "caption", "title", "heading", "formula",
                "reference", "author", "affiliation")
        for b in blocks:
            if b["type"] in KEEP or not b["text"].strip():
                continue
            cx = (b["bbox"][0] + b["bbox"][2]) / 2.0
            cy = (b["bbox"][1] + b["bbox"][3]) / 2.0
            if not any(fx0 <= cx <= fx1 and fy0 <= cy <= fy1
                       for fx0, fy0, fx1, fy1 in page_fig_boxes):
                continue
            labelish = ((b.get("size") or body_size) <= 0.85 * body_size
                        or len(b["text"].strip()) <= 14)
            if labelish:
                b["type"] = "figure_label"
                b["masked_chars"] = nospace_len(b["text"])

        ordered = order_blocks(blocks, pg["cols"], pg["gutters"])
        for i, b in enumerate(ordered):
            b["order"] = i
            b["page_order"] = i
            b["id"] = "p%d-b%03d" % (pno + 1, i)
            all_blocks.append(b)
        headings.extend([b for b in ordered if b["type"] == "heading"])
        out_pages.append({**base, "columns": len(pg["cols"]),
                          "column_bands": [[r2(a), r2(b)] for a, b in pg["cols"]],
                          "gutters": [[r2(a), r2(b)] for a, b in pg["gutters"]],
                          "text_layer_chars": text_layer,
                          "dropped_running_chars": sum(nospace_len(x) for x in dropped),
                          "n_blocks": len(ordered), "n_lines": len(lines),
                          "dropped_running_text": dropped[:8],
                          "body_size": r2(body_size), "empty": False})

    # post-passes: front matter, bibliography, then the section tree
    for b in all_blocks:
        b.pop("spans", None)
    merged_title = merge_title_continuations(all_blocks)
    if merged_title:
        warnings.append({"code": "title_merged", "extra_lines": merged_title,
                         "detail": "document title spans %d visual lines; they have "
                                   "been joined into one block so the second line does "
                                   "not become a phantom section" % (merged_title + 1)})
    merged_head = merge_heading_continuations(all_blocks)
    if merged_head:
        warnings.append({"code": "heading_merged", "merged_lines": merged_head,
                         "detail": "%d heading line(s) were joined into the heading they "
                                   "continue (a heading never ends on a connective)"
                                   % merged_head})
    front = extract_front_matter(all_blocks, figures)
    # convenience mirror: consumers often just want the title string
    front["title_text"] = (front.get("title") or {}).get("text", "") \
        if isinstance(front.get("title"), dict) else (front.get("title") or "")
    references, ref_heading = extract_references(all_blocks)
    headings = [b for b in all_blocks if b["type"] == "heading" and
                (not front["title"] or b["text"] != front["title"]["text"])]
    sections = build_sections(headings, out_pages,
                              (front.get("title") or {}).get("size"))

    if doc_cols >= 2:
        odd = [p["page"] for p in out_pages
               if not p.get("empty") and p.get("columns") == 1 and p.get("n_lines", 0) > 25]
        if odd:
            warnings.append({"code": "column_template_mismatch", "pages": odd,
                             "detail": "body is %d-column; these pages were parsed as "
                                       "single column - verify order" % doc_cols})
    if any(p.get("empty") for p in out_pages):
        warnings.append({"code": "ocr_required",
                         "pages": [p["page"] for p in out_pages if p.get("empty")],
                         "detail": "pages without a text layer cannot be parsed "
                                   "structurally; transcribe them with the vision/OCR "
                                   "path and mark them as ocr_sourced"})

    stats = doc_stats(all_blocks, out_pages, sections, tables, figures)
    result = {
        "schema": SCHEMA,
        "source": {"path": os.path.basename(path), "sha256": sha256_file(path),
                   "bytes": os.path.getsize(path), "pages": n_pages},
        "engine": {"name": "pymupdf", "version": getattr(fitz, "__version__", ""),
                   "mupdf": _mupdf_version(),
                   "python": sys.version.split()[0], "pipeline": SCHEMA},
        "document": {"pages": n_pages, "column_template": doc_cols,
                     "has_text_layer": stats["text_layer_chars"] > 0},
        "pages": out_pages, "sections": sections,
        "metadata": front, "references": references,
        "tables": [t for t in tables if not t.get("rejected")],
        "tables_rejected": [t for t in tables if t.get("rejected")],
        "figures": figures,
        "blocks": all_blocks, "stats": stats, "warnings": warnings,
    }
    return result, doc


def _char_overlap(a, b):
    """Fraction of characters of `a` that also occur in `b` (multiset)."""
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    common = sum(min(n, cb[ch]) for ch, n in ca.items())
    return common / max(1, len(a))


# --------------------------------------------------------------------------- #
# 9. front matter + bibliography
# --------------------------------------------------------------------------- #
ABSTRACT_RE = re.compile(r"^\s*(abstract|summary|摘\s*要)\s*[:：]?\s*", re.I)
REF_ENTRY_RE = re.compile(r"^\s*(\[\s*\d{1,3}\s*\]|\[\s*[A-Z]\d+\s*\]|\d{1,3}[.)]\s+)")
AFFIL_RE = re.compile(r"(@|university|institute|laborator|department|school|college|"
                      r"inc\.|ltd|corp|research|academy|大学|学院|研究所|实验室|"
                      r"\b(google|microsoft|deepmind|facebook|meta|amazon|nvidia|ibm|intel|"
                      r"openai|bytedance|tencent|alibaba|baidu|huawei|brain|ai\b|labs?\b))",
                      re.I)
ARXIV_RE = re.compile(r"^\s*arxiv:\s*\S*", re.I)
# a line that is only a footnote marker + text is never part of the abstract
FOOTMARK_RE = re.compile(r"^\s*[∗*†‡§¶#¶‖]+")
# publisher licence / attribution boilerplate is not paper content
LICENSE_RE = re.compile(r"^\s*(provided proper attribution|licensed under|"
                        r"creative commons|permission to make digital|"
                        r"this work is licensed|copyright\s*(©|\(c\))|©\s*\d{4})", re.I)


def _in_any(bbox, boxes):
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    for b in boxes:
        if b[0] - 2 <= cx <= b[2] + 2 and b[1] - 2 <= cy <= b[3] + 2:
            return True
    return False


NAME_RE = re.compile(r"^[^\Wa-z0-9_][\w.'\-]*(?:\s+[^\Wa-z0-9_][\w.'\-]*){0,3}$")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def _emails_in(text):
    return EMAIL_RE.findall(text)


def merge_title_continuations(blocks):
    """Glue a title that is set on several lines back into one block.

    The paragraph builder deliberately never glues heading-like lines together,
    so a two-line title ("AN IMAGE IS WORTH 16X16 WORDS:" /
    "TRANSFORMERS FOR IMAGE RECOGNITION AT SCALE") arrives as two blocks and the
    second one survives as a phantom level-1 section.  A continuation is only
    accepted when the evidence is unambiguous: same page, same font size, a
    tight vertical gap, no comma/semicolon (author lists are comma separated)
    and no sentence-final full stop.  Returns the number of merged lines.
    """
    p1 = [b for b in blocks if b["page"] == 1 and b["text"].strip()
          and b["type"] not in ("margin_artifact", "figure", "table", "caption")]
    if not p1:
        return 0
    sizes = sorted(float(b.get("size") or 0) for b in p1)
    med = sizes[len(sizes) // 2]
    head = max(p1, key=lambda b: (float(b.get("size") or 0), -b["bbox"][1]))
    if float(head.get("size") or 0) < max(1.15 * med, 1.0):
        return 0
    merged = 0
    while merged < 3:
        nxt = None
        for b in blocks:
            if b is head or b["page"] != 1 or not b["text"].strip():
                continue
            if b["type"] in ("margin_artifact", "figure", "table", "caption",
                             "author", "affiliation"):
                continue
            if abs(float(b.get("size") or 0) - float(head["size"])) > 0.8:
                continue
            gap = b["bbox"][1] - head["bbox"][3]
            if not (-0.5 * float(head["size"]) <= gap <= 1.9 * float(head["size"])):
                continue
            if _iou(b["bbox"], head["bbox"]) > 0.05:
                continue                       # same visual line, not a continuation
            if nxt is None or b["bbox"][1] < nxt["bbox"][1]:
                nxt = b
        if nxt is None:
            break
        t = nxt["text"].strip()
        if len(t) > 140 or t.endswith((".", "。")) or re.search(r"[,;@]", t):
            break
        head["text"] = (head["text"].rstrip() + " " + t).strip()
        head["raw"] = (head.get("raw") or head["text"]) + "\n" + (nxt.get("raw") or t)
        head["bbox"] = union_bbox([head["bbox"], nxt["bbox"]])
        head["n_lines"] = int(head.get("n_lines") or 1) + int(nxt.get("n_lines") or 1)
        blocks.remove(nxt)
        merged += 1
    if merged:
        for i, b in enumerate([x for x in blocks if x["page"] == 1]):
            b["order"] = i
            b["page_order"] = i
            b["id"] = "p1-b%03d" % i
    return merged


CONNECTIVE_TAIL = {
    "for", "of", "the", "and", "with", "in", "on", "to", "a", "an", "by",
    "from", "as", "at", "or", "via", "using", "under", "over", "into",
    "between", "without", "within", "toward", "towards", "is", "are",
}


def merge_heading_continuations(blocks):
    """Join a heading that was broken over several lines.

    A heading never ends on a connective ("... Transformers for"), so such a
    block is the first half of a multi-line banner (BERT's appendix title is set
    on three bold lines).  Without this pass each line becomes its own section
    and the tree grows phantom parents.  Only same page, same size, same weight
    and a tight gap are accepted.
    """
    merged = 0
    for page_no in sorted({b["page"] for b in blocks if b["type"] == "heading"}):
        page = [b for b in blocks if b["page"] == page_no]
        i = 0
        while i < len(page):
            head = page[i]
            i += 1
            if head["type"] != "heading" or not head["text"].strip():
                continue
            for _ in range(2):
                words = head["text"].strip().split()
                if not words or words[-1].strip(":.,;").lower() not in CONNECTIVE_TAIL:
                    break
                nxt = None
                for b in page:
                    if b is head or b["type"] != "heading" or not b["text"].strip():
                        continue
                    if abs(float(b.get("size") or 0) - float(head["size"])) > 0.6:
                        continue
                    if bool(b.get("bold")) != bool(head.get("bold")):
                        continue
                    gap = b["bbox"][1] - head["bbox"][3]
                    if not (-0.5 * float(head["size"]) <= gap <= 1.6 * float(head["size"])):
                        continue
                    if nxt is None or b["bbox"][1] < nxt["bbox"][1]:
                        nxt = b
                if nxt is None:
                    break
                head["text"] = (head["text"].rstrip() + " " + nxt["text"].strip()).strip()
                head["raw"] = (head.get("raw") or head["text"]) + "\n" + (nxt.get("raw") or nxt["text"])
                head["bbox"] = union_bbox([head["bbox"], nxt["bbox"]])
                head["n_lines"] = int(head.get("n_lines") or 1) + int(nxt.get("n_lines") or 1)
                blocks.remove(nxt)
                page.remove(nxt)
                merged += 1
    if merged:
        for page_no in sorted({b["page"] for b in blocks}):
            for i, b in enumerate([x for x in blocks if x["page"] == page_no]):
                b["order"] = i
                b["page_order"] = i
                b["id"] = "p%d-b%03d" % (page_no, i)
    return merged


def extract_front_matter(blocks, figures=()):
    """Title / authors / affiliations / abstract from the first body blocks.

    Only used when the page-1 layout is a recognisable paper header; anything
    unexpected leaves the fields empty instead of guessing.
    """
    fm = {"title": None, "authors": [], "affiliations": [], "emails": [],
          "abstract": None, "abstract_pages": [], "keywords": []}
    fig_boxes = [f["bbox"] for f in figures if f["page"] == 1]
    p1 = [b for b in blocks if b["page"] == 1 and not _in_any(b["bbox"], fig_boxes)]
    if not p1:
        return fm
    abs_block = None
    for b in blocks:
        if ABSTRACT_RE.match(b["text"]) and len(b["text"]) < 40:
            abs_block = b
            break
    # the title is the visually dominant block above the abstract
    title = None
    pool = [b for b in p1 if len(b["text"].strip()) >= 8 and
            b["type"] not in ("margin_artifact", "author", "affiliation")]
    if pool:
        med = sorted(float(b.get("size") or 0) for b in pool)[len(pool) // 2]
        strong = [b for b in pool if float(b.get("size") or 0) >= max(1.15 * med, 9.0)]
        if strong:
            if abs_block is not None:
                ai = blocks.index(abs_block)
                strong = [b for b in strong if blocks.index(b) < ai] or strong
            title = max(strong, key=lambda x: (float(x.get("size") or 0),
                                               1 if x.get("bold") else 0))
    if title is not None:
        fm["title"] = {"text": title["text"], "page": title["page"],
                       "bbox": title["bbox"], "size": title.get("size")}
    if abs_block is not None:
        start = blocks.index(abs_block)
        head = ABSTRACT_RE.sub("", abs_block["text"]).strip()
        parts = [head] if head else []
        pages = [abs_block["page"]] if head else []
        base_size = None
        for b in blocks[start + 1:start + 9]:
            if b["type"] in ("heading", "title", "table", "figure"):
                break
            t = b["text"].strip()
            if not t:
                continue
            sz = float(b.get("size") or 0)
            if FOOTMARK_RE.match(t):
                break
            if base_size is None:
                base_size = sz          # the abstract's own size sets the scale
            # a smaller run is a footnote / licence line, not the abstract
            if sz < 0.9 * base_size or b["type"] in ("footnote", "margin_artifact"):
                break
            parts.append(t)
            pages.append(b["page"])
        fm["abstract"] = " ".join(x for x in parts if x).strip() or None
        fm["abstract_pages"] = sorted(set(pages))
        abs_idx = start
    else:
        abs_idx = 10 ** 9
    if title is not None:
        ti = blocks.index(title) if title in blocks else -1
        stop = abs_idx if abs_idx < 10 ** 9 else (ti + 12 if ti >= 0 else 12)
        for b in (blocks[ti + 1:stop] if ti >= 0 else []):
            if b["page"] != 1:
                break
            t = b["text"].strip()
            if not t or len(t) > 220 or _in_any(b["bbox"], fig_boxes):
                continue
            if ABSTRACT_RE.match(t):
                continue
            if AFFIL_RE.search(t):
                for e in _emails_in(t):
                    if e.lower() not in [x.lower() for x in fm["emails"]]:
                        fm["emails"].append(e)
                if "@" not in t:
                    fm["affiliations"].append({"text": t, "page": b["page"],
                                               "bbox": b["bbox"]})
                continue
            for part in re.split(r"(?:,|\band\b|&|;)", t):
                p = re.sub(r"[\d*†‡§¶∗\u00b9\u00b2\u00b3]+", "", part).strip()
                if 2 < len(p) < 60 and not AFFIL_RE.search(p) and NAME_RE.match(p):
                    fm["authors"].append(p)
    seen = set()
    uniq = []
    for a in fm["authors"]:
        if a.lower() not in seen:
            seen.add(a.lower())
            uniq.append(a)
    fm["authors"] = uniq
    seen = set()
    affil = []
    for a in fm["affiliations"]:
        k = a["text"].lower()
        if k not in seen:
            seen.add(k)
            affil.append(a)
    fm["affiliations"] = affil
    for b in p1:
        if b is title:
            continue
        t = b["text"].strip()
        # a glued footnote marker ("1Fine-tuning code ...") or a URL is not an
        # affiliation, even when the host name matches one ("google-research")
        foot_glued = bool(re.match(r"^\s*\d{1,2}[A-Za-z]", t)) or "http" in t.lower()
        if AFFIL_RE.search(t) and len(t) <= 220 and not foot_glued \
                and not _in_any(b["bbox"], fig_boxes):
            b["type"] = "affiliation"
        elif fm["authors"] and any(a in t for a in fm["authors"]) and len(t) <= 220:
            b["type"] = "author"
    return fm


def extract_references(blocks):
    """Split the bibliography into numbered entries with page/bbox provenance."""
    refs = []
    start = None
    for i, b in enumerate(blocks):
        if REF_HEAD_RE.match(b["text"]):
            start = i
            break
    if start is None:
        return refs, None
    body = []
    for b in blocks[start + 1:]:
        if b["type"] in ("heading", "title", "table", "figure", "caption"):
            break
        b["type"] = "reference"
        body.append(b)
    cur = None
    for b in body:
        lines = (b.get("raw") or b["text"]).split("\n")
        buf, first = [], True
        for ln in lines:
            if REF_ENTRY_RE.match(ln) and buf:
                if cur:
                    cur["text"] = " ".join(x.strip() for x in buf).strip()
                    refs.append(cur)
                cur = {"id": None, "text": "", "page": b["page"], "bbox": b["bbox"],
                       "section_block": b["id"]}
                buf = [REF_ENTRY_RE.sub("", ln, count=1)]
                first = False
            elif REF_ENTRY_RE.match(ln) and not buf:
                buf = [REF_ENTRY_RE.sub("", ln, count=1)]
            else:
                buf.append(ln)
        if buf:
            if cur is None:
                cur = {"id": None, "text": "", "page": b["page"], "bbox": b["bbox"],
                       "section_block": b["id"]}
                buf = [REF_ENTRY_RE.sub("", x, count=1) for x in buf]
            cur["text"] = " ".join(([cur["text"]] if cur["text"] else []) +
                                   [" ".join(y.strip() for y in buf)]).strip()
            refs.append(cur)
            cur = None
    for i, r in enumerate(refs, 1):
        r["id"] = "R%d" % i
        r["text"] = re.sub(r"\s+", " ", r.pop("section_block") and r["text"] or r["text"]).strip()
    return refs, blocks[start]


def _make_block(grp, pno, col, body_size, force_type=None):
    text = join_lines(grp)
    bb = union_bbox([l["bbox"] for l in grp])
    btype = force_type or classify(text, max(l["size"] for l in grp), body_size,
                                   any(l["bold"] for l in grp),
                                   all(l["mono"] for l in grp), len(grp))
    return {"page": pno + 1, "bbox": bb, "column": col, "type": btype,
            "text": text, "raw": "\n".join(l["text"] for l in grp),
            "n_lines": len(grp), "size": r2(max(l["size"] for l in grp)),
            "bold": any(l["bold"] for l in grp), "italic": any(l["italic"] for l in grp),
            "mono": all(l["mono"] for l in grp), "font": grp[0]["font"],
            "sup_sub": sup_sub_text(grp), "rotated": any(l["rotated"] for l in grp)}


def _norm(text):
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", text)).strip().lower()


def _iou(a, b):
    if not a or not b:
        return 0.0
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def build_sections(headings, out_pages, title_size=None):
    sections, stack = [], []
    sizes = {round(h["size"], 1) for h in headings}
    # the document title is not a section, but its size is the top rung of the
    # type scale; without it every level below shifts up by one
    if title_size:
        sizes.add(round(float(title_size), 1))
    sizes = sorted(sizes, reverse=True)
    for h in headings:
        lvl = heading_level(h, sizes)
        h["level"] = lvl  # keep the level on the block so text.md can mirror
        while stack and stack[-1][0] >= lvl:
            stack.pop()
        stack.append((lvl, h["text"].strip()))
        sections.append({"id": "S%d" % (len(sections) + 1),
                         "title": h["text"].strip(), "level": lvl,
                         "page": h["page"], "bbox": h["bbox"], "block_id": h["id"],
                         "path": " / ".join(s[1][:48] for s in stack)})
    return sections


def doc_stats(blocks, pages, sections, tables, figures):
    tl = sum(p.get("text_layer_chars", 0) for p in pages)
    dropped = sum(p.get("dropped_running_chars", 0) for p in pages)
    masked = sum(b.get("masked_chars", 0) if b["type"] == "figure_label"
                 else nospace_len(b["text"]) for b in blocks
                 if b["type"] in ("figure_label", "margin_artifact"))
    emitted = sum(nospace_len(b["text"]) for b in blocks
                  if b["type"] not in ("figure_label", "margin_artifact"))
    expect = max(0, tl - dropped - masked)
    return {
        "n_pages_parsed": len([p for p in pages if not p.get("empty")]),
        "text_layer_chars": tl,
        "dropped_running_chars": dropped,
        "masked_figure_label_chars": masked,
        "emitted_chars": emitted,
        "char_recall": round(emitted / expect, 4) if expect else None,
        "char_recall_vs_full_layer": round(emitted / tl, 4) if tl else None,
        "n_blocks": len(blocks),
        "n_headings": len([b for b in blocks if b["type"] == "heading"]),
        "n_formulas": len([b for b in blocks if b["type"] == "formula"]),
        "n_tables": len(tables),
        "n_table_cells": sum(len(t["cells"]) for t in tables),
        "n_figures": len(figures),
        "n_sections": len(sections),
        "blocks_with_bbox": sum(1 for b in blocks if b.get("bbox")),
        "blocks_with_page": sum(1 for b in blocks if isinstance(b.get("page"), int)),
        "types": _type_hist(blocks),
    }


def _type_hist(blocks):
    d = {}
    for b in blocks:
        d[b["type"]] = d.get(b["type"], 0) + 1
    return dict(sorted(d.items()))