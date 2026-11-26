#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_robustness.py -- abnormal input handling + three-column evidence.

    python tests/test_robustness.py            # every case
    python tests/test_robustness.py three      # only cases whose name matches

No pytest, no network, no scoring endpoint.  Each assertion prints one ASCII
line `PASS  <case>  <assertion>` or `FAIL  <case>  <assertion>  [detail]`, and
the process exits 1 if anything failed.  A UTF-8 detail log (Chinese allowed)
is written to tests/_work/robust/last_run.txt.

Every bad input is generated on the spot into `tests/_work/robust/` -- nothing
binary is added to the bundle.  For each of them the bar is:

  (a) the exit code equals what outputs/SKILL.md declares (or falls inside the
      declared range), and
  (b) stdout/stderr contain no `Traceback (most recent call last)` and do carry
      a readable English reason (SKILL.md §7: "stderr 带异常信息").

SKILL.md declarations used as the oracle (quoted verbatim in robustness.md):
  §2  "退出码即结论：`0` 成功；`2` 用法错误；`3` **该 PDF 无文本层，必须转 OCR
      分支**；`4` 自检不通过"
  §7  "加密/损坏 | 打开异常，退出码 2，stderr 带异常信息"

This file is deliberately independent of test_engine.py (three synthetic
Chinese/English/scanned fixtures); both entry points can be run in any order.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys

import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.dirname(HERE)
SCRIPTS = os.path.join(BUNDLE, "scripts")
WORK = os.path.join(HERE, "_work", "robust")
PY = sys.executable

sys.path.insert(0, SCRIPTS)
from make_fixtures import META, save_pdf  # noqa: E402

RESULTS = []          # (case, assertion, ok, detail)
TRACEBACK = "Traceback (most recent call last)"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def check(case, assertion, ok, detail=""):
    RESULTS.append((case, assertion, bool(ok), detail))


def ascii_safe(s):
    return str(s).encode("ascii", "backslashreplace").decode("ascii")


def run(args, **kw):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, **kw)


def load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def case_dir(case):
    d = os.path.join(WORK, case)
    os.makedirs(d, exist_ok=True)
    return d


def parse(case, pdf, extra=()):
    """Run the CLI; returns (completed_process, outdir)."""
    out = os.path.join(case_dir(case), "out")
    os.makedirs(out, exist_ok=True)
    p = run([PY, os.path.join(SCRIPTS, "parse_pdf.py"), pdf, "--out", out,
             "--no-overlay"] + list(extra))
    return p, out


def no_traceback(case, p, where="stdout+stderr"):
    blob = (p.stdout or "") + (p.stderr or "")
    check(case, "no python traceback (%s)" % where, TRACEBACK not in blob,
          "tail=%r" % blob[-300:])


def readable(case, p, want=None):
    """Exit-2 paths must explain themselves on stderr, in plain English."""
    err = p.stderr or ""
    ok = ("ERROR" in err) and re.search(r"[A-Za-z]{3,}", err) is not None
    check(case, "stderr has a readable English reason", bool(ok),
          "stderr=%r" % err.strip()[:200])
    if want:
        hit = any(w.lower() in err.lower() for w in want)
        check(case, "reason mentions %s" % "/".join(want), hit,
              "stderr=%r" % err.strip()[:200])


def exits(case, p, expected, why):
    check(case, "exit==%d (%s)" % (expected, why), p.returncode == expected,
          "exit=%d stderr=%r" % (p.returncode, (p.stderr or "").strip()[:160]))


# --------------------------------------------------------------------------- #
# PDF builders (all synthetic, all written under tests/_work/robust)
# --------------------------------------------------------------------------- #
def build_zero_byte(path):
    with open(path, "wb"):
        pass


def build_not_a_pdf(path):
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("This is a plain text file with a .pdf extension.\n" * 40)


def build_zero_page(path):
    """PyMuPDF refuses to *save* a document with zero pages, so hand-assemble
    the smallest legal PDF whose page tree is empty (/Count 0)."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [] /Count 0 >>"]
    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offs = []
    for i, body in enumerate(objs, 1):
        offs.append(len(buf))
        buf += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(buf)
    buf += b"xref\n0 %d\n" % (len(objs) + 1) + b"0000000000 65535 f \n"
    for off in offs:
        buf += b"%010d 00000 n \n" % off
    buf += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref))
    with open(path, "wb") as fh:
        fh.write(bytes(buf))


N_BODY_LINES = 24


def _fill_single_page(doc):
    page = doc.new_page(width=595, height=842)
    page.insert_text((56, 100), "1 INTRODUCTION", fontsize=15, fontname="Times-Bold")
    y = 100
    for i in range(N_BODY_LINES):
        y += 15
        page.insert_text((56, y),
                         "Body line %02d of a single column page used by the "
                         "rotation and running-head checks." % i,
                         fontsize=10.5, fontname="Times-Roman")


def build_one_page(path):
    doc = fitz.open()
    _fill_single_page(doc)
    doc.set_metadata(dict(META, title="one-page fixture", author="test_robustness"))
    save_pdf(doc, path)
    doc.close()


def build_rotated(src, path):
    """Same page as one-page.pdf, but the page dictionary carries /Rotate 90."""
    doc = fitz.open(src)
    doc[0].set_rotation(90)
    save_pdf(doc, path)
    doc.close()


def build_encrypted(src, path):
    doc = fitz.open(src)
    doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256,
             owner_pw="owner-secret", user_pw="user-secret")
    doc.close()


def build_multi_page(path, n):
    doc = fitz.open()
    for k in range(n):
        page = doc.new_page(width=595, height=842)
        page.insert_text((56, 90), "%d SECTION %d" % (k + 1, k + 1),
                         fontsize=15, fontname="Times-Bold")
        y = 90
        for i in range(30):
            y += 15
            page.insert_text((56, y), "Page %d body line %02d: lorem ipsum dolor "
                             "sit amet consectetur." % (k + 1, i), fontsize=10.5,
                             fontname="Times-Roman")
    doc.set_metadata(dict(META, title="multi-page fixture", author="test_robustness"))
    save_pdf(doc, path)
    doc.close()


# three columns: 60 mm wide, 6 mm gutter (17.0 pt > merge_rows' 14 pt max_gap,
# so a line from column N is never glued to a line from column N+1)
MM = 72.0 / 25.4
COL_W = 60.0 * MM
GUT = 6.0 * MM
COL_LEFT = (595.0 - (3 * COL_W + 2 * GUT)) / 2.0


def wrap_width(text, width, size, fontname="Times-Roman"):
    """Break `text` so every line measures <= `width` points.

    Counting characters is not enough: 34 chars at 10.5 pt is ~178 pt, i.e.
    wider than a 60 mm (170.08 pt) column, and an over-wide line reaches into
    the gutter and is then (correctly) read as a cross-column block.  A real
    3-column paper never lets its body lines overrun the column box, so the
    fixture must not either -- otherwise the test would measure the fixture's
    mistake, not the engine's column order.
    """
    words, lines, cur = text.split(), [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if cur and fitz.get_text_length(cand, fontname=fontname,
                                        fontsize=size) > width:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines

THREE_COL_SECTIONS = [
    ("1 INTRODUCTION", [
        "Sparse retrieval is the first stage of most production search stacks and "
        "it decides which passages the reranker is allowed to look at.",
        "The candidate pool is usually fixed by folklore instead of measurement, "
        "so its cost hides inside the latency budget of the whole system.",
        "We measure the pool directly and report where extra candidates stop "
        "paying for themselves on three standard collections.",
    ]),
    ("2 METHOD", [
        "The first stage is BM25 with default parameters and the second stage is "
        "a single cross encoder checkpoint held fixed for every run.",
        "Each configuration is scored on the same qrels with the same cut off so "
        "that differences come from the pool size alone.",
        "Timing is taken on one machine with the index resident in memory and the "
        "median of three repeats is reported for every point.",
    ]),
    ("3 RESULTS", [
        "Recall keeps climbing with the pool while reciprocal rank saturates well "
        "before the largest pool we tested.",
        "Past roughly one thousand candidates the reranker spends most of its "
        "budget on passages it will never place in the top ten.",
        "The turnover point moves with collection size but not with the tokenizer "
        "used to build the index.",
    ]),
]


def build_three_col(path):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    body, head, lh = 10.5, 14.0, 13.0

    def put(x, baseline, text, size, bold=False):
        page.insert_text((x, baseline), text, fontsize=size,
                         fontname="Times-Bold" if bold else "Times-Roman")

    # full-width front matter: it must be spanning blocks, not column lines
    put(COL_LEFT, 56, "THREE COLUMN LAYOUT STRESS TEST", 18, bold=True)
    put(COL_LEFT, 76, "Alice Zhang, Bob Li", 10.5)
    put(COL_LEFT, 96, "Institute for Retrieval Research", 8.5)
    put(COL_LEFT, 118, "Abstract", 11, bold=True)
    y = 134
    for ln in wrap_width("We study how a three column body is linearised by the "
                         "parser and whether every numbered heading survives the "
                         "column split intact.", 3 * COL_W + 2 * GUT - 4, 9.5):
        put(COL_LEFT, y, ln, 9.5)
        y += 12
    top = y + 12

    for ci, (head_txt, paras) in enumerate(THREE_COL_SECTIONS):
        x = COL_LEFT + ci * (COL_W + GUT)
        put(x, top, head_txt, head, bold=True)
        cy = top + head + 8
        for para in paras:
            for ln in wrap_width(para, COL_W - 4, body):
                put(x, cy, ln, body)
                cy += lh
            cy += 5
    doc.set_metadata(dict(META, title="three-col fixture", author="test_robustness"))
    save_pdf(doc, path)
    doc.close()


def truncation_source():
    """40% of a real paper when the corpus is at hand, else 40% of a synthetic
    6-page PDF, so the case still runs on a checkout without corpus/*.pdf."""
    for cand in (os.path.join(BUNDLE, "corpus", "resnet.pdf"),
                 os.path.join(os.path.dirname(BUNDLE), "corpus", "resnet.pdf")):
        if os.path.exists(cand):
            return cand, "corpus/resnet.pdf"
    src = os.path.join(case_dir("truncated"), "source-6p.pdf")
    if not os.path.exists(src):
        build_multi_page(src, 6)
    return src, "synthetic 6-page"


def build_truncated(path, src, frac=0.40):
    with open(src, "rb") as fh:
        data = fh.read()
    keep = max(1, int(len(data) * frac))
    with open(path, "wb") as fh:
        fh.write(data[:keep])
    return keep, len(data)


# --------------------------------------------------------------------------- #
# case 1: zero-byte file
# --------------------------------------------------------------------------- #
def case_zero_byte():
    case = "zero-byte"
    pdf = os.path.join(case_dir(case), "zero-byte.pdf")
    build_zero_byte(pdf)
    check(case, "fixture is 0 bytes", os.path.getsize(pdf) == 0,
          "size=%d" % os.path.getsize(pdf))
    p, out = parse(case, pdf)
    exits(case, p, 2, "SKILL.md S7: corrupt/unopenable -> 2")
    no_traceback(case, p)
    readable(case, p, ["cannot open", "PDF"])
    check(case, "no doc.json written for an unreadable file",
          not os.path.exists(os.path.join(out, "doc.json")), "doc.json exists")


# --------------------------------------------------------------------------- #
# case 2: text file with a .pdf extension
# --------------------------------------------------------------------------- #
def case_not_a_pdf():
    case = "not-a-pdf"
    pdf = os.path.join(case_dir(case), "not-a-pdf.pdf")
    build_not_a_pdf(pdf)
    p, out = parse(case, pdf)
    exits(case, p, 2, "SKILL.md S7: corrupt/unopenable -> 2")
    no_traceback(case, p)
    readable(case, p, ["cannot open", "PDF"])
    check(case, "no doc.json written for an unreadable file",
          not os.path.exists(os.path.join(out, "doc.json")), "doc.json exists")


# --------------------------------------------------------------------------- #
# case 3: truncated PDF (first 40% of the bytes)
# --------------------------------------------------------------------------- #
def case_truncated():
    case = "truncated"
    src, label = truncation_source()
    pdf = os.path.join(case_dir(case), "truncated.pdf")
    kept, total = build_truncated(pdf, src)
    check(case, "fixture is the first 40%% of %s" % label,
          kept == int(total * 0.40) and kept < total,
          "kept=%d of %d" % (kept, total))
    p, out = parse(case, pdf)
    no_traceback(case, p)
    check(case, "exit is a documented code (0/2/3/4)",
          p.returncode in (0, 2, 3, 4), "exit=%d" % p.returncode)
    doc_json = os.path.join(out, "doc.json")
    if p.returncode == 2:
        # clean refusal of a file mupdf could not repair into any page
        readable(case, p, ["page", "truncated"])
    elif p.returncode in (0, 4):
        doc = load(doc_json) if os.path.exists(doc_json) else {}
        check(case, "partial parse kept at least one complete page",
              doc.get("stats", {}).get("n_pages_parsed", 0) >= 1,
              "n_pages_parsed=%s" % doc.get("stats", {}).get("n_pages_parsed"))
        check(case, "partial parse carries warnings",
              bool(doc.get("warnings")), "warnings=%s" % doc.get("warnings"))
        cr = doc.get("stats", {}).get("char_recall")
        check(case, "partial parse char_recall sane (None or <=1.05)",
              cr is None or cr <= 1.05, "char_recall=%s" % cr)
    else:  # 3
        # legitimate only if the repaired pages really have no text layer
        doc = load(doc_json) if os.path.exists(doc_json) else {}
        empty = [x["page"] for x in doc.get("pages", []) if x.get("empty")]
        codes = [w.get("code") for w in doc.get("warnings", [])]
        check(case, "exit=3 backed by empty pages + ocr_required warning",
              bool(empty) and "ocr_required" in codes,
              "empty=%s warnings=%s" % (empty, codes))


# --------------------------------------------------------------------------- #
# case 4: password-protected PDF
# --------------------------------------------------------------------------- #
def case_encrypted():
    case = "encrypted"
    d = case_dir(case)
    plain = os.path.join(d, "plain.pdf")
    build_one_page(plain)
    pdf = os.path.join(d, "encrypted.pdf")
    build_encrypted(plain, pdf)
    probe = fitz.open(pdf)
    check(case, "fixture really needs a password", bool(probe.needs_pass),
          "needs_pass=%s" % probe.needs_pass)
    probe.close()
    p, out = parse(case, pdf)
    exits(case, p, 2, "SKILL.md S7: encrypted -> 2")
    no_traceback(case, p)
    readable(case, p, ["encrypted", "password"])
    check(case, "no doc.json written for an encrypted file",
          not os.path.exists(os.path.join(out, "doc.json")), "doc.json exists")


# --------------------------------------------------------------------------- #
# case 5: single page, no running head
# --------------------------------------------------------------------------- #
def case_one_page():
    case = "one-page"
    pdf = os.path.join(case_dir(case), "one-page.pdf")
    build_one_page(pdf)
    p, out = parse(case, pdf)
    exits(case, p, 0, "SKILL.md S2: success -> 0")
    no_traceback(case, p)
    doc = load(os.path.join(out, "doc.json"))
    check(case, "selfcheck.ok (no false running-head on a single page)",
          doc["selfcheck"]["ok"] is True,
          "errors=%s warnings=%s" % (doc["selfcheck"]["errors"],
                                     doc["selfcheck"]["warnings"]))
    check(case, "dropped_running_chars==0 on a header-less single page",
          doc["pages"][0].get("dropped_running_chars") == 0,
          "dropped=%s text=%s" % (doc["pages"][0].get("dropped_running_chars"),
                                  doc["pages"][0].get("dropped_running_text")))
    cr = doc["stats"].get("char_recall")
    check(case, "char_recall in [0.90, 1.05]", cr is not None and 0.90 <= cr <= 1.05,
          "char_recall=%s" % cr)
    check(case, "single column page", doc["pages"][0].get("columns") == 1,
          "columns=%s" % doc["pages"][0].get("columns"))


# --------------------------------------------------------------------------- #
# case 6: page with /Rotate 90
# --------------------------------------------------------------------------- #
def case_rotated():
    case = "rotated"
    d = case_dir(case)
    base = os.path.join(d, "one-page.pdf")
    build_one_page(base)
    pdf = os.path.join(d, "rotated.pdf")
    build_rotated(base, pdf)
    p, out = parse(case, pdf)
    exits(case, p, 0, "SKILL.md S2: success -> 0")
    no_traceback(case, p)
    doc = load(os.path.join(out, "doc.json"))
    cr = doc["stats"].get("char_recall")
    check(case, "char_recall in [0.90, 1.05] (no text lost)", cr is not None
          and 0.90 <= cr <= 1.05, "char_recall=%s" % cr)
    text = " ".join(b["text"] for b in doc["blocks"]
                    if b["type"] not in ("figure_label", "margin_artifact"))
    check(case, "first and last body lines survive the rotation",
          "Body line 00" in text and "Body line %02d" % (N_BODY_LINES - 1) in text,
          "missing=%s" % [x for x in ("Body line 00",
                                      "Body line %02d" % (N_BODY_LINES - 1))
                          if x not in text])
    pg = doc["pages"][0]
    # The engine has no pages[].rotation field (see robustness.md); the applied
    # /Rotate is observable as a swapped page rectangle, 595x842 -> 842x595.
    check(case, "page geometry reflects /Rotate 90 (width/height swapped)",
          abs(pg["width"] - 842) < 1 and abs(pg["height"] - 595) < 1,
          "width=%s height=%s" % (pg["width"], pg["height"]))
    check(case, "selfcheck.ok on a rotated page", doc["selfcheck"]["ok"] is True,
          "errors=%s" % doc["selfcheck"]["errors"])


# --------------------------------------------------------------------------- #
# case 7: three-column body
# --------------------------------------------------------------------------- #
def case_three_col():
    case = "three-col"
    pdf = os.path.join(case_dir(case), "three-col.pdf")
    build_three_col(pdf)
    p, out = parse(case, pdf)
    exits(case, p, 0, "SKILL.md S2: success -> 0")
    no_traceback(case, p)
    doc = load(os.path.join(out, "doc.json"))
    pages = doc["pages"]
    tmpl = doc["document"].get("column_template")

    cols = max([x.get("columns") or 0 for x in pages] or [0])
    check(case, "(a) columns>=3 (pages[] or column_template)",
          cols >= 3 or (tmpl or 0) >= 3,
          "pages.columns=%s column_template=%s" % (
              [x.get("columns") for x in pages], tmpl))
    check(case, "column_template == 3 on a 3x60mm body", tmpl == 3,
          "column_template=%s" % tmpl)

    titles = [re.sub(r"\s+", " ", s["title"]).strip().upper()
              for s in doc["sections"]]
    want = [t for t, _ in THREE_COL_SECTIONS]
    missing = [t for t in want if t not in titles]
    check(case, "(b) all three numbered headings are sections", not missing,
          "missing=%s sections=%s" % (missing, titles))

    cr = doc["stats"].get("char_recall")
    check(case, "(c) char_recall in [0.90, 1.05] (no lost characters)",
          cr is not None and 0.90 <= cr <= 1.05, "char_recall=%s" % cr)

    ordered = sorted([b for b in doc["blocks"] if b.get("column", -1) >= 0],
                     key=lambda b: b["order"])
    cs = [b["column"] for b in ordered]
    check(case, "(d) all three columns carry blocks", sorted(set(cs)) == [0, 1, 2],
          "columns present=%s" % sorted(set(cs)))
    check(case, "(d) column sequence never goes backwards (no 1->3->2)", all(
        cs[i] <= cs[i + 1] for i in range(len(cs) - 1)), "columns=%s" % cs)
    per_col = {}
    for b in ordered:
        per_col.setdefault(b["column"], []).append(b["bbox"][1])
    bad = [c for c, ys in per_col.items() if ys != sorted(ys)]
    check(case, "(d) y order is monotone inside every column", not bad,
          "non_monotone_cols=%s" % bad)

    # nothing in the body band may be read as a cross-column block: such a
    # block is emitted after the whole band by order_blocks(), i.e. column-0
    # text would appear at the end of the page (after 3 RESULTS).
    body_top = min(b["bbox"][1] for b in doc["blocks"]
                   if b["type"] == "heading" and b.get("column", -1) >= 0)
    stray = [(b["id"], b["column"], round(b["bbox"][0], 1), b["text"][:40])
             for b in doc["blocks"] if b["bbox"][1] >= body_top - 1
             and b.get("column", -1) < 0]
    check(case, "(d) no body block is emitted as cross-column", not stray,
          "stray=%s" % stray)
    # bands are ink extents inside the 60 mm boxes (ragged right), so they are
    # a little narrower than 60 mm; what must hold is three disjoint bands that
    # fill the 3x60 + 2x6 = 192 mm text block, with an ink-free strip between.
    bands = pages[0]["column_bands"]
    gs = pages[0]["gutters"]
    widths = [b1 - b0 for b0, b1 in bands]
    gwidths = [g1 - g0 for g0, g1 in gs]
    span = bands[-1][1] - bands[0][0]
    check(case, "3 disjoint 60mm bands filling a 192mm text block",
          len(bands) == 3 and len(gs) == 2
          and all(w >= 40 * MM for w in widths)
          and 186 * MM <= span <= 198 * MM
          and all(g >= 4 * MM for g in gwidths)
          and bands[0][1] <= bands[1][0] < bands[1][1] <= bands[2][0],
          "bands=%s widths=%s gutters=%s span=%.1f" % (
              bands, [round(w, 1) for w in widths],
              [round(g, 1) for g in gwidths], span))


# --------------------------------------------------------------------------- #
# case 8: PDF with zero pages
# --------------------------------------------------------------------------- #
def case_empty():
    case = "empty"
    pdf = os.path.join(case_dir(case), "empty.pdf")
    build_zero_page(pdf)
    probe = fitz.open(pdf)
    check(case, "fixture really has 0 pages", probe.page_count == 0,
          "page_count=%d" % probe.page_count)
    probe.close()
    p, out = parse(case, pdf)
    exits(case, p, 2, "SKILL.md S7: unparseable -> 2 (not the OCR route)")
    no_traceback(case, p)
    readable(case, p, ["0 pages"])
    blob = (p.stdout or "") + (p.stderr or "")
    check(case, "no division-by-zero crash", "ZeroDivisionError" not in blob,
          "tail=%r" % blob[-200:])
    check(case, "no doc.json written for a 0-page file",
          not os.path.exists(os.path.join(out, "doc.json")), "doc.json exists")


# --------------------------------------------------------------------------- #
# case 9 (extra): malformed --pages argument
# --------------------------------------------------------------------------- #
def case_bad_pages_arg():
    case = "bad-pages"
    pdf = os.path.join(case_dir("one-page"), "one-page.pdf")
    build_one_page(pdf)
    p, _out = parse(case, pdf, ["--pages", "1-x"])
    exits(case, p, 2, "SKILL.md S2: usage error -> 2")
    no_traceback(case, p, "stdout+stderr")


# --------------------------------------------------------------------------- #
CASES = [
    ("zero", case_zero_byte),
    ("notpdf", case_not_a_pdf),
    ("trunc", case_truncated),
    ("encrypt", case_encrypted),
    ("one", case_one_page),
    ("rotate", case_rotated),
    ("three", case_three_col),
    ("empty", case_empty),
    ("badpages", case_bad_pages_arg),
]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    os.makedirs(WORK, exist_ok=True)
    want = [c for c in CASES if not argv or any(a in c[0] for a in argv)]

    for _name, fn in want:
        try:
            fn()
        except Exception as exc:                     # noqa: BLE001
            check(_name, "case raised", False, "%s: %s" % (type(exc).__name__, exc))

    fails = 0
    for case, assertion, ok, detail in RESULTS:
        if ok:
            print("PASS  %-10s  %s" % (case, ascii_safe(assertion)))
        else:
            fails += 1
            print("FAIL  %-10s  %s  [%s]" % (case, ascii_safe(assertion),
                                             ascii_safe(detail)[:300]))
    print("")
    print("%d checks, %d failed" % (len(RESULTS), fails))

    log = os.path.join(WORK, "last_run.txt")
    with io.open(log, "w", encoding="utf-8", newline="\n") as fh:
        for case, assertion, ok, detail in RESULTS:
            fh.write("%s  %s  %s  %s\n" % ("PASS" if ok else "FAIL", case,
                                           assertion, detail))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
