#!/usr/bin/env python3
"""baseline_compare.py -- quantify what a bare agent gets from the same PDF.

The baseline is deliberately the *default* thing an agent does with PyMuPDF:
`"".join(page.get_text("text") for page in doc)`.  No layout pass, no table
finder, no provenance.  Every metric below is computed from the PDF itself, so
the comparison can be re-run by anyone:

  * running-header lines that survive into the body text
  * figure-internal label characters that survive into the body text
  * headings that are glued into the middle of a prose line
  * column switches that go back to the left column (2-column interleaving)
  * structural output: blocks with page+bbox, sections, tables, cells

Usage:
  python baseline_compare.py paper.pdf --doc out/paper/doc.json [--json report.json]

`--doc` is the engine's own doc.json for the same PDF (produced by
parse_pdf.py); the running-header list, the gutter geometry and the block
inventory come from there.  Exit code 0 always: this is a measurement, not a
gate.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore


def _lines_of_page(page):
    """Naive reading order: PyMuPDF's own block/line order."""
    out = []
    for blk in page.get_text("dict").get("blocks", []):
        if blk.get("type") != 0:
            continue
        for ln in blk.get("lines", []):
            txt = "".join(s.get("text", "") for s in ln.get("spans", [])).strip()
            if txt:
                out.append((txt, tuple(ln["bbox"])))
    return out


def _col_of(bbox, bands):
    cx = (bbox[0] + bbox[2]) / 2.0
    for i, (x0, x1) in enumerate(bands):
        if x0 - 1.0 <= cx <= x1 + 1.0:
            return i
    return None


def measure(pdf_path, doc_path):
    doc = fitz.open(pdf_path)
    meta = json.load(open(doc_path, encoding="utf-8"))
    pages = {p["page"]: p for p in meta["pages"]}
    blocks = meta["blocks"]

    naive_lines, hdr_hits, label_chars = 0, 0, 0
    interleave = 0
    two_col_pages = 0
    per_page = []

    header_set = set()
    for p in meta["pages"]:
        for t in (p.get("dropped_running_text") or []):
            t = t.strip()
            # page numbers alone are not the interesting part of a running head
            if len(t) >= 8 and not t.isdigit():
                header_set.add(t)

    for i, page in enumerate(doc, start=1):
        raw = page.get_text("text")
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        naive_lines += len(lines)
        hits = sum(1 for ln in lines if ln.strip() in header_set)
        hdr_hits += hits

        pg = pages.get(i, {})
        bands = pg.get("column_bands") or []
        flips = 0
        # geometry gate: a real two-column page has two comparably wide bands
        # separated by a narrow gutter.  A figure hole in a single-column page
        # can produce two "bands" with a huge gap in the middle - that is not a
        # column decision and must not be scored as interleaving.
        two_col_geom = False
        if len(bands) == 2:
            content = bands[1][1] - bands[0][0]
            gutter = bands[1][0] - bands[0][1]
            w0, w1 = bands[0][1] - bands[0][0], bands[1][1] - bands[1][0]
            two_col_geom = (content > 0 and gutter <= 0.12 * content
                            and min(w0, w1) >= 0.22 * content)
        if two_col_geom and not pg.get("empty"):
            seq = []
            for txt, bb in _lines_of_page(page):
                if len(txt) < 3:
                    continue
                c = _col_of(bb, bands)
                if c is None:
                    continue          # spanning line: not a column decision
                seq.append(c)
            # a page only counts as two-column when both bands carry real text;
            # a wide table can create a second band on a single-column page
            if seq.count(0) >= 8 and seq.count(1) >= 8:
                two_col_pages += 1
                # a return to the left column after right-column text means the
                # extractor left something behind in the left column
                seen_right = False
                for c in seq:
                    if c == 1:
                        seen_right = True
                    elif seen_right:
                        flips += 1
                        seen_right = False
            interleave += flips
        per_page.append({"page": i, "naive_lines": len(lines),
                         "header_lines": hits, "interleavings": flips})

    two_col_doc = int((meta.get("document") or {}).get("column_template") or 1) >= 2
    if not two_col_doc:
        interleave = None
        two_col_pages = 0
        for r in per_page:
            r["interleavings"] = None

    for b in blocks:
        if b["type"] == "figure_label":
            label_chars += int(b.get("masked_chars") or 0)

    # headings that a naive dump cannot separate from prose: their text is
    # present but not at the start of a line
    naive_text = "\n".join(p.get_text("text") for p in doc)
    naive_lines_set = [ln.strip() for ln in naive_text.splitlines() if ln.strip()]
    heads = [b for b in blocks if b["type"] in ("heading", "title")]
    glued = 0
    for h in heads:
        t = h["text"].strip()
        if not t:
            continue
        if any(ln == t or ln.startswith(t) for ln in naive_lines_set):
            continue                # stayed a line of its own
        if t[:40] in naive_text:
            glued += 1              # merged into a longer line
    tables = meta.get("tables", [])
    cells = sum(int(t.get("n_rows") or 0) * int(t.get("n_cols") or 0) for t in tables)

    naive_chars = len("".join(naive_text.split()))
    skill_chars = meta["stats"].get("emitted_chars")
    res = {
        "file": os.path.basename(pdf_path),
        "pages": len(doc),
        "baseline": {
            "method": "pymupdf page.get_text('text') in document order",
            "chars": naive_chars,
            "lines": naive_lines,
            "blocks_with_bbox": 0,
            "sections": 0,
            "tables": 0,
            "table_cells": 0,
            "running_header_lines": hdr_hits,
            "figure_label_chars_in_body": label_chars,
            "headings_glued_into_prose": glued,
            "cross_column_interleavings": interleave,
            "two_column_pages": two_col_pages,
        },
        "skill": {
            "method": meta.get("schema"),
            "chars": skill_chars,
            "lines": None,
            "blocks_with_bbox": sum(1 for b in blocks if b.get("bbox")),
            "sections": len(meta.get("sections", [])),
            "tables": len(tables),
            "table_cells": cells,
            "running_header_lines": 0,
            "figure_label_chars_in_body": 0,
            "headings_glued_into_prose": 0,
            "cross_column_interleavings": 0,
            "dropped_running_chars": meta["stats"].get("dropped_running_chars"),
            "char_recall": meta["stats"].get("char_recall"),
            "selfcheck_ok": (meta.get("selfcheck") or {}).get("ok"),
        },
        "page_metrics": per_page,
    }
    doc.close()
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--doc", required=True, help="doc.json produced by parse_pdf.py")
    ap.add_argument("--json", help="write the full result here")
    a = ap.parse_args()
    r = measure(a.pdf, a.doc)
    b, s = r["baseline"], r["skill"]
    print("baseline vs skill: %s (%d pages)" % (r["file"], r["pages"]))
    rows = [
        ("chars", b["chars"], s["chars"]),
        ("blocks with page+bbox", b["blocks_with_bbox"], s["blocks_with_bbox"]),
        ("sections", b["sections"], s["sections"]),
        ("tables / cells", "%d / %d" % (b["tables"], b["table_cells"]),
         "%d / %d" % (s["tables"], s["table_cells"])),
        ("running-header lines kept", b["running_header_lines"], s["running_header_lines"]),
        ("figure-label chars in body", b["figure_label_chars_in_body"],
         s["figure_label_chars_in_body"]),
        ("headings glued into prose", b["headings_glued_into_prose"],
         s["headings_glued_into_prose"]),
        ("cross-column interleavings", b["cross_column_interleavings"],
         s["cross_column_interleavings"]),
    ]
    for name, x, y in rows:
        x = "n/a" if x is None else x
        y = "n/a" if y is None else y
        print("  %-28s %-14s %s" % (name, x, y))
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("wrote", a.json)


if __name__ == "__main__":
    sys.exit(main())
