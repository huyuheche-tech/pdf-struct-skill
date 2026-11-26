#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_fixtures.py -- generate the three synthetic PDFs used by tests/.

    python outputs/scripts/make_fixtures.py [--out tests/fixtures]

Writes (deterministic: same input -> same text layer, same geometry):

    cjk-2col.pdf    A4, Chinese two-column body: full-width title / authors /
                    摘要 / two columns (1 引言, 2 相关工作, 2.1 检索增强,
                    3 方法, 4 实验, 参考文献), a 3x3 Chinese table drawn with
                    vector rules, one "图 1 系统结构" caption.
    title-wrap.pdf  Letter, English single column: title set on two lines
                    (first line ends with ':'), comma-separated author line,
                    Abstract, 3 sections; "2.1 SETUP AND METRICS" is set at
                    body size in ALL CAPS (ICLR camera-ready style).
    scanned.pdf     title-wrap.pdf rendered to a 200 dpi PNG and re-wrapped
                    into a one-page PDF with *no text layer*.

Every fixture is synthetic.  They are not real papers, journal pages or
scanner output; they exist to pin layout invariants of pdf_struct.py.
The Chinese face is a system font (msyh.ttc / simsun.ttc) embedded as a real
font, so the page carries a text layer rather than drawn glyph outlines.
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.dirname(os.path.dirname(HERE))
DEFAULT_OUT = os.path.join(BUNDLE, "tests", "fixtures")

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
]
CJK_FONT_NAME = "cjk"

# fixed metadata so repeated runs differ only by PyMuPDF's own /ID stamp
META = {"creationDate": "D:20240101000000Z", "modDate": "D:20240101000000Z",
        "creator": "make_fixtures.py", "producer": "make_fixtures.py"}

# --------------------------------------------------------------------------- #
# CJK content (no line may start with a CN/NUM heading marker unless intended)
# --------------------------------------------------------------------------- #
CJK_TITLE = "面向中文科技文献的结构化解析方法研究"
# one wide author/affiliation band: wider than 62% of the text block, so the
# gutter detector does not count it as a "short" voter that crosses the gutter
CJK_AUTHORS = "张伟　李娜　王强　赵敏　清华大学计算机科学与技术系　北京 100084　zhangwei@tsinghua.edu.cn"
CJK_ABSTRACT = (
    "本文研究中文科技文献的版面结构解析问题。现有方法大多只在英文语料上验证，"
    "对中文断行、全角标点与双栏混排缺乏稳定约束，导致阅读顺序在栏间跳变。"
    "我们提出一种以投影和几何规则为主的解析流程，逐块记录页码与坐标，"
    "使正文中的每一句都可以回溯到原页位置，并对无法确定的版面给出显式标记。"
    "在合成的双栏中文页面上，该流程可以稳定恢复栏序、章节层级与表格结构。"
)
CJK_PARAS = [
    ("引言", [
        "随着预印本数量的增长，自动解析论文结构已经成为检索系统的基础环节，"
        "解析结果既要保留阅读顺序，也要保留每个段落在页面上的原始位置。",
        "中文排版以全角字符为主，行末不插入空格，断行处也不添加连字符，"
        "因此按空格切词的英文流水线在中文页面上会系统性地丢失行边界信息。",
        "本文以几何线索为主，字符统计为辅，避免对语种做过多先验假设，"
        "同时把每一个判断的依据写进输出，方便人工复核与后续追责。",
    ]),
    ("相关工作", [
        "版面分析通常分为自顶向下的投影方法和自底向上的连通域方法两类，"
        "前者速度快但对倾斜扫描件敏感，后者鲁棒但需要较重的后处理。",
        "检索增强的做法是在生成之前拼接外部证据，从而缓解事实性错误，"
        "我们沿用这一设定，但把证据限定为同一文档内的相邻段落。",
        "解析质量的评价指标包括段落召回率与章节路径的完整程度，"
        "所有指标都基于人工标注的页面结构进行计算并给出置信说明。",
    ]),
    ("检索增强", [
        "具体做法是先用一阶召回得到候选段落，再用交叉编码器重排，"
        "并在重排之后回填每个段落对应的页码与坐标，保证结果可追溯。",
        "为了避免候选池过大带来的延迟，我们固定重排深度并只调整召回规模，"
        "这样不同配置之间的差异可以归因到候选数量这一个变量上。",
    ]),
    ("方法", [
        "流程分为四步：提取文本行、检测栏与栏间空白、按几何规则分组、最后排序。",
        "分组时不允许跨栏拼接，任何跨越栏间空白的行都被当作通栏内容单独处理。",
        "表格由矢量线框提供边界，单元格文本再按词框重新拼装，避免多行单元格串行。",
    ]),
    ("实验", [
        "在合成页面上，栏数恢复、章节路径与表格行列数都与构造时一致，"
        "字符召回率在百分之九十九以上，说明没有段落被静默丢弃。",
        "我们同时检查了块与栏间空白的关系，确认没有块同时跨越两栏，"
        "这一条是阅读顺序正确的前提，也是本流程最容易出错的地方。",
        "对于没有文本层的扫描页，流程不做任何猜测，而是直接交给视觉转录分支。",
    ]),
]
CJK_CELLS = [["模型", "准确率", "参数量"],
             ["基线", "82.1", "12M"],
             ["本文", "85.4", "9M"]]
CJK_REFS = [
    "[1] 张伟. 中文版面分析综述. 软件学报, 2021.",
    "[2] 李娜. 双栏文档的阅读顺序恢复. 计算机学报, 2022.",
    "[3] 王强. 结构化解析的可追溯性. 中文信息学报, 2023.",
]

# --------------------------------------------------------------------------- #
# English content for title-wrap.pdf / scanned.pdf
# --------------------------------------------------------------------------- #
EN_TITLE_1 = "SCALING SPARSE RETRIEVAL:"
EN_TITLE_2 = "A CONTROLLED STUDY OF HYBRID RERANKING"
EN_AUTHORS = "Alice Zhang, Bob Li, Carol Wu"
EN_AFFIL = "Institute for Retrieval Research"
EN_ABSTRACT = (
    "We study how the size of a sparse retrieval candidate pool interacts with a "
    "fixed cross-encoder reranker. Holding the reranker constant and sweeping the "
    "pool from one hundred to four thousand passages, we isolate the point where "
    "additional candidates stop paying for themselves. The effect is stable across "
    "three collections and does not depend on the tokenizer."
)
EN_SECTIONS = [
    ("1 INTRODUCTION", 1, [
        "Sparse retrieval followed by dense reranking is the default recipe for "
        "first-stage ranking in production search systems.",
        "The recipe hides a free parameter: how many candidates the reranker is "
        "allowed to see. Practitioners set it by folklore rather than measurement.",
        "This paper measures it directly and reports where the curve turns over.",
    ]),
    ("2 METHOD", 1, [
        "We fix the first stage to BM25 with default parameters and fix the second "
        "stage to a single cross-encoder checkpoint.",
        "Every configuration is scored on the same qrels with the same cut-off, so "
        "differences are attributable to the pool size alone.",
    ]),
    ("2.1 SETUP AND METRICS", 2, [
        "Each run reports recall at one hundred and mean reciprocal rank at ten.",
        "We repeat every configuration three times with different negative samples "
        "and report the median, because the tail of the distribution is heavy.",
        "Timing is measured on a single machine with the index held in memory.",
    ]),
    ("3 RESULTS", 1, [
        "Recall keeps climbing with the pool while reciprocal rank saturates early.",
        "Past roughly one thousand candidates the reranker spends most of its budget "
        "on passages it will never place in the top ten.",
        "The turnover point moves with collection size but not with the tokenizer.",
    ]),
]
EN_REFS = [
    "[1] Robertson S. The probabilistic relevance framework. 2009.",
    "[2] Nogueira R. Passage re-ranking with transformers. 2019.",
]


def save_pdf(doc, path):
    """Write deterministically: no fresh /ID, no wall-clock stamps."""
    try:
        doc.save(path, garbage=3, deflate=True, no_new_id=True, reproducible=True)
    except TypeError:                      # older PyMuPDF without these flags
        doc.save(path, garbage=3, deflate=True)


def pick_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("no CJK system font found (msyh.ttc / simsun.ttc)")


def cjk_width(text, size):
    """Advance width of CJK text: one em per ideograph, half em for ASCII."""
    w = 0.0
    for ch in text:
        w += size * (1.0 if ord(ch) > 0x2E7F else 0.5)
    return w


def wrap_cjk(text, per_line):
    """Slice a Chinese paragraph into fixed-width visual lines (no spaces)."""
    flat = "".join(text.split())
    return [flat[i:i + per_line] for i in range(0, len(flat), per_line)] or [""]


def build_cjk(path):
    fontfile = pick_font()
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)     # A4
    page.insert_font(fontname=CJK_FONT_NAME, fontfile=fontfile)

    left, right_edge = 56.0, 539.0
    col_w = 232.0
    col2_x = right_edge - col_w                    # 307
    gutter0 = left + col_w                          # 288
    body_size, head_size = 10.5, 12.0
    lh = 14.5

    def put(x, baseline, text, size, bold=False):
        page.insert_text((x, baseline), text, fontsize=size,
                         fontname=CJK_FONT_NAME,
                         render_mode=2 if bold else 0)

    # ---- running head ------------------------------------------------------ #
    put(56, 66, "第 39 卷 第 4 期　软件学报　Vol. 39 No. 4", 9)
    page.draw_line((56, 74), (539, 74), width=0.8)

    # ---- title / authors / abstract (full width) ------------------------- #
    tw = cjk_width(CJK_TITLE, 20)
    put((595 - tw) / 2.0, 122, CJK_TITLE, 20)
    put(left, 146, CJK_AUTHORS, body_size)

    put(left, 172, "摘要", head_size)
    y = 188
    for ln in wrap_cjk(CJK_ABSTRACT, 44):
        put(left, y, ln, body_size)
        y += lh
    put(left, y + 4, "关键词：版面分析；双栏混排；结构解析", body_size)
    page.draw_line((56, y + 12), (539, y + 12), width=0.6)

    # ---- left column ------------------------------------------------------ #
    cy = y + 32
    put(left, cy, "1 " + CJK_PARAS[0][0], head_size, bold=True)
    cy += 20
    for para in CJK_PARAS[0][1]:
        for ln in wrap_cjk(para, 22):
            put(left, cy, ln, body_size)
            cy += lh
    cy += 8
    put(left, cy, "2 " + CJK_PARAS[1][0], head_size, bold=True)
    cy += 20
    for para in CJK_PARAS[1][1]:
        for ln in wrap_cjk(para, 22):
            put(left, cy, ln, body_size)
            cy += lh
        cy += 6
    cy += 2
    put(left, cy, "2.1 " + CJK_PARAS[2][0], head_size, bold=True)
    cy += 20
    for para in CJK_PARAS[2][1]:
        for ln in wrap_cjk(para, 22):
            put(left, cy, ln, body_size)
            cy += lh
        cy += 6

    # ---- right column ----------------------------------------------------- #
    ry = y + 32
    put(col2_x, ry, "3 " + CJK_PARAS[3][0], head_size, bold=True)
    ry += 20
    for para in CJK_PARAS[3][1][:2]:
        for ln in wrap_cjk(para, 22):
            put(col2_x, ry, ln, body_size)
            ry += lh
        ry += 6

    # vector figure placeholder + its caption (a real, if tiny, figure region)
    ry += 4
    fig_rect = fitz.Rect(col2_x + 30, ry, col2_x + col_w - 30, ry + 48)
    page.draw_rect(fig_rect, color=(0.45, 0.45, 0.45), width=0.8)
    ry += 48 + 16
    put(col2_x, ry, "图 1 系统结构", body_size)
    ry += 44

    for ln in wrap_cjk(CJK_PARAS[3][1][2], 22):
        put(col2_x, ry, ln, body_size)
        ry += lh
    ry += 26
    put(col2_x, ry, "表 1 精度对比", body_size)
    ry += 26

    # 3x3 table drawn with vector rules (so PyMuPDF's grid finder can see it)
    t_top, t_h, cw = ry, 78.0, col_w / 3.0
    rows = 3
    for r in range(rows + 1):
        yy = t_top + r * (t_h / rows)
        page.draw_line((col2_x, yy), (col2_x + col_w, yy), width=0.8)
    for c in range(4):
        xx = col2_x + c * cw
        page.draw_line((xx, t_top), (xx, t_top + t_h), width=0.8)
    for r in range(rows):
        for c in range(3):
            cell = CJK_CELLS[r][c]
            put(col2_x + c * cw + 6, t_top + r * (t_h / rows) + 20, cell, 9)
    ry = t_top + t_h + 26

    put(col2_x, ry, "4 " + CJK_PARAS[4][0], head_size, bold=True)
    ry += 20
    for para in CJK_PARAS[4][1]:
        for ln in wrap_cjk(para, 22):
            put(col2_x, ry, ln, body_size)
            ry += lh
        ry += 6
    put(col2_x, ry, "参考文献", head_size, bold=True)
    ry += 18
    for ref in CJK_REFS:
        put(col2_x, ry, ref, 8.5)
        ry += 12

    doc.set_metadata(dict(META, title="cjk-2col fixture", author="make_fixtures"))
    try:
        doc.subset_fonts()          # embed only the glyphs used (~12 MB -> ~40 KB)
    except Exception:
        pass
    save_pdf(doc, path)
    doc.close()


# --------------------------------------------------------------------------- #
def wrap_latin(text, per_line):
    words, lines, cur = text.split(), [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if len(cand) > per_line and cur:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def _page_title_wrap(doc):
    page = doc.new_page(width=612, height=792)     # US Letter
    left, rmax = 72.0, 540.0
    body_size = 10.5
    lh = 14.0

    def put(x, baseline, text, size, bold=False, italic=False):
        page.insert_text((x, baseline), text, fontsize=size,
                         fontname="Times-Bold" if bold else "Times-Roman",
                         render_mode=2 if italic else 0)

    # two-line title; the first line ends with a colon
    put(left, 110, EN_TITLE_1, 22, bold=True)
    put(left, 138, EN_TITLE_2, 22, bold=True)
    put(left, 166, EN_AUTHORS, 11)
    put(left, 182, EN_AFFIL, 9)

    y = 214
    put(left, y, "Abstract", 12, bold=True)
    y += 18
    for ln in wrap_latin(EN_ABSTRACT, 92):
        put(left, y, ln, body_size)
        y += lh
    y += 14

    for title, _lvl, paras in EN_SECTIONS:
        put(left, y, title, 12 if title[0].isdigit() and "." not in title.split()[0]
            else body_size, bold="." not in title.split()[0])
        y += 18 if "." not in title.split()[0] else 16
        for para in paras:
            for ln in wrap_latin(para, 92):
                put(left, y, ln, body_size)
                y += lh
            y += 6
        y += 6

    put(left, y, "References", 11, bold=True)
    y += 16
    for ref in EN_REFS:
        put(left, y, ref, 9)
        y += 12
    return page


def build_title_wrap(path):
    doc = fitz.open()
    _page_title_wrap(doc)
    doc.set_metadata(dict(META, title="title-wrap fixture", author="make_fixtures"))
    save_pdf(doc, path)
    doc.close()


def build_scanned(path, dpi=200):
    doc = fitz.open()
    _page_title_wrap(doc)
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    doc.close()

    out = fitz.open()
    w = pix.width * 72.0 / dpi
    h = pix.height * 72.0 / dpi
    p2 = out.new_page(width=w, height=h)
    p2.insert_image(fitz.Rect(0, 0, w, h), pixmap=pix)
    out.set_metadata(dict(META, title="scanned fixture", author="make_fixtures"))
    save_pdf(out, path)
    text = out[0].get_text("text")
    out.close()
    if text.strip():
        raise SystemExit("scanned.pdf still carries a text layer: %r"
                         % text[:80])


def main(argv=None):
    ap = argparse.ArgumentParser(description="generate synthetic test PDFs")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    targets = [
        ("cjk-2col.pdf", build_cjk),
        ("title-wrap.pdf", build_title_wrap),
        ("scanned.pdf", build_scanned),
    ]
    for name, fn in targets:
        p = os.path.join(args.out, name)
        fn(p)
        print("wrote %-16s %8d bytes" % (name, os.path.getsize(p)))
    print("fixtures dir: %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
