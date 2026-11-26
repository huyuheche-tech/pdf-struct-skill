#!/usr/bin/env python3
"""parse_pdf.py -- CLI front end of the pdf-parse skill.

    python parse_pdf.py INPUT.pdf --out OUTDIR [--pages 1-6] [--dpi 110]

Writes (all UTF-8):
    OUTDIR/doc.json        ordered blocks + sections + tables + figures + stats
    OUTDIR/text.md         human/machine readable reading-order text with
                           per-block provenance comments (page + bbox)
    OUTDIR/report.json     per-page integrity report + warnings + self-check
    OUTDIR/tables/T*.csv   one CSV per detected table (row/col owned)
    OUTDIR/figures/F*.png  cropped figure images referenced by the JSON
    OUTDIR/overlay/*.png   page render with block boxes + reading-order numbers

Exit codes: 0 ok, 2 usage error, 3 unreadable/no text layer (OCR route needed),
            4 self-check found a hard violation.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_struct import parse_document  # noqa: E402

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = None


COLORS = {
    "title": (200, 0, 0),
    "heading": (220, 80, 0),
    "body": (0, 90, 200),
    "formula": (140, 0, 160),
    "table": (0, 140, 90),
    "figure": (0, 140, 90),
    "caption": (140, 110, 0),
    "footnote": (110, 110, 110),
    "code": (60, 60, 60),
    "reference": (90, 90, 160),
}


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


def _md(s):
    """Escape leading '#' so original text such as a table cell '# layers'
    is not rendered as a markdown heading by accident."""
    out = []
    for ln in s.split("\n"):
        out.append("\\" + ln if ln.lstrip().startswith("#") else ln)
    return "\n".join(out)


def write_text_md(doc, path, fig_map):
    L = []
    fig_caption = {f["id"]: (f.get("caption") or "figure") for f in doc["figures"]}
    L.append("# %s\n" % doc["source"]["path"])
    L.append("<!-- schema=%s pages=%d column_template=%d sha256=%s -->\n" % (
        doc["schema"], doc["source"]["pages"], doc["document"]["column_template"],
        doc["source"]["sha256"]))
    by_page = {}
    for b in doc["blocks"]:
        by_page.setdefault(b["page"], []).append(b)
    for p in doc["pages"]:
        pno = p["page"]
        L.append("\n<!-- ===== page %d | columns=%s | gutters=%s -->" % (
            pno, p.get("columns"), p.get("gutters")))
        if p.get("empty"):
            L.append("<!-- [FLAG] page %d has no text layer: route to OCR/vision "
                     "and record uncertainty, never guess -->\n" % pno)
            continue
        for b in sorted(by_page.get(pno, []), key=lambda b: b["page_order"]):
            if b["type"] in ("figure_label", "margin_artifact"):
                # text inside artwork: reported in doc.json for traceability,
                # deliberately kept out of the reading text
                continue
            prov = ("<!-- %s | type=%s | col=%s | bbox=%s -->" % (
                b["id"], b["type"], b["column"], ",".join("%.1f" % v for v in b["bbox"])))
            t = b["type"]
            if t in ("title", "heading"):
                hashes = "#" * min(6, max(2, 1 + (b.get("level") or 1)))
                L.append(prov)
                L.append("%s %s\n" % (hashes, b["text"].strip()))
            elif t == "table":
                L.append(prov)
                L.append("[table %s]" % b.get("table_id"))
                L.append(_md(b["text"]) + "\n")
            elif t == "figure":
                fid = b.get("figure_id")
                src = fig_map.get(fid, "")
                # the caption also appears as its own `caption` block right after
                # this line; keep the alt text complete (no hard cut) so a reader
                # never sees a sentence severed mid-word
                cap = " ".join((fig_caption.get(fid) or "figure").split())
                L.append(prov)
                L.append("![%s](%s)\n" % (cap.replace("]", r"\]"), src))
            elif t == "formula":
                L.append(prov)
                L.append("$$ %s $$\n" % b["text"].strip())
            else:
                L.append(prov)
                L.append(_md(b["text"].strip()) + "\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def write_tables(doc, outdir):
    tdir = os.path.join(outdir, "tables")
    ensure_dir(tdir)
    for t in doc["tables"]:
        p = os.path.join(tdir, "%s.csv" % t["id"])
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            for row in t["rows"]:
                w.writerow(row)
        t["csv"] = "tables/%s.csv" % t["id"]
    return [t.get("csv") for t in doc["tables"]]


def write_figures(doc, pdf, outdir):
    fdir = os.path.join(outdir, "figures")
    ensure_dir(fdir)
    fig_map = {}
    if Image is None:
        return fig_map
    for f in doc["figures"]:
        try:
            page = pdf[f["page"] - 1]
            clip = fitz.Rect(f["bbox"])
            if clip.width < 24 or clip.height < 24:
                continue
            pix = page.get_pixmap(clip=clip, dpi=150)
            rel = "figures/%s.png" % f["id"]
            pix.save(os.path.join(outdir, rel))
            f["image"] = rel
            fig_map[f["id"]] = rel
        except Exception as exc:  # pragma: no cover
            f["image_error"] = str(exc)
    return fig_map


def write_overlays(doc, pdf, outdir, dpi):
    if Image is None:
        return []
    odir = os.path.join(outdir, "overlay")
    ensure_dir(odir)
    made = []
    by_page = {}
    for b in doc["blocks"]:
        by_page.setdefault(b["page"], []).append(b)
    for p in doc["pages"]:
        pno = p["page"]
        page = pdf[pno - 1]
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        d = ImageDraw.Draw(img)
        sc = dpi / 72.0
        for b in sorted(by_page.get(pno, []), key=lambda b: b["page_order"]):
            x0, y0, x1, y1 = [v * sc for v in b["bbox"]]
            col = COLORS.get(b["type"], (0, 0, 0))
            d.rectangle([x0, y0, x1, y1], outline=col, width=2)
            label = "%d" % b["page_order"]
            d.text((x0 + 2, max(0, y0 - 11)), label, fill=col)
        if p.get("gutters"):
            for g0, g1 in p["gutters"]:
                d.line([g0 * sc, 0, g0 * sc, img.height], fill=(255, 0, 255), width=1)
                d.line([g1 * sc, 0, g1 * sc, img.height], fill=(255, 0, 255), width=1)
        rel = "overlay/page-%02d.png" % pno
        img.save(os.path.join(outdir, rel))
        made.append(rel)
    return made


def selfcheck(doc):
    """Structural invariants that must hold for a trustworthy parse."""
    errs, warns = [], []
    blocks = doc["blocks"]
    if not blocks:
        errs.append("no_blocks")
    for b in blocks:
        if not b.get("bbox") or len(b["bbox"]) != 4:
            errs.append("block_without_bbox:%s" % b.get("id"))
        if not isinstance(b.get("page"), int) or b["page"] < 1:
            errs.append("block_without_page:%s" % b.get("id"))
        if not (b.get("text") or b.get("figure_id")):
            warns.append("empty_block:%s" % b.get("id"))
    for p in doc["pages"]:
        if p.get("empty"):
            continue
        ids = [b["page_order"] for b in blocks if b["page"] == p["page"]]
        if ids and sorted(ids) != list(range(len(ids))):
            errs.append("order_not_contiguous:p%d" % p["page"])
    # column purity: a block classified into a column must not cross a gutter
    for p in doc["pages"]:
        for g0, g1 in p.get("gutters", []):
            for b in blocks:
                if b["page"] != p["page"] or b.get("column", -1) < 0:
                    continue
                if b["bbox"][0] < g1 - 1 and b["bbox"][2] > g0 + 1:
                    errs.append("column_block_crosses_gutter:%s" % b["id"])
    st = doc["stats"]
    if st.get("char_recall") is not None and st["char_recall"] < 0.90:
        warns.append("char_recall_low:%.3f" % st["char_recall"])
    if st.get("blocks_with_bbox") != st.get("n_blocks"):
        errs.append("bbox_coverage_incomplete")
    for t in doc["tables"]:
        if t["n_rows"] < 2 or t["n_cols"] < 2:
            warns.append("degenerate_table:%s" % t["id"])
        if t.get("fill_rate", 1) < 0.5:
            warns.append("sparse_table:%s" % t["id"])
    return {"errors": errs, "warnings": warns,
            "ok": not errs}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Layout-aware PDF structure parser")
    ap.add_argument("pdf")
    ap.add_argument("--out", "-o", required=True)
    ap.add_argument("--pages", default=None, help="e.g. 1-6 or 1,3,5")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--no-overlay", action="store_true")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--no-text-md", action="store_true")
    args = ap.parse_args(argv)

    if not os.path.exists(args.pdf):
        print("ERROR: no such file: %s" % args.pdf)
        return 2
    max_pages = None
    if args.pages:
        spec = args.pages.strip()
        if "-" in spec:
            a, b = spec.split("-")[:2]
            max_pages = int(b)
        else:
            max_pages = max(int(x) for x in spec.split(","))
    ensure_dir(args.out)

    try:
        doc, pdf = parse_document(args.pdf, max_pages=max_pages, dpi=args.dpi)
    except Exception as exc:
        print("ERROR: parse failed: %s: %s" % (type(exc).__name__, exc))
        return 3

    fig_map = {} if args.no_figures else write_figures(doc, pdf, args.out)
    write_tables(doc, args.out)
    overlays = [] if args.no_overlay else write_overlays(doc, pdf, args.out, args.dpi)
    chk = selfcheck(doc)
    doc["selfcheck"] = chk
    doc["artifacts"] = {"text_md": "text.md", "overlays": overlays,
                        "figures": list(fig_map.values()),
                        "tables": [t.get("csv") for t in doc["tables"]]}
    with open(os.path.join(args.out, "doc.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    if not args.no_text_md:
        write_text_md(doc, os.path.join(args.out, "text.md"), fig_map)
    report = {
        "input": doc["source"],
        "engine": doc["engine"],
        "document": doc["document"],
        "stats": doc["stats"],
        "warnings": doc["warnings"],
        "selfcheck": chk,
        "pages": [{k: p.get(k) for k in
                   ("page", "columns", "gutters", "text_layer_chars", "n_blocks", "empty")}
                  for p in doc["pages"]],
    }
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    st = doc["stats"]
    print("parsed: %s" % doc["source"]["path"])
    print("pages=%d blocks=%d headings=%d formulas=%d tables=%d figures=%d" % (
        st["n_pages_parsed"], st["n_blocks"], st["n_headings"], st["n_formulas"],
        st["n_tables"], st["n_figures"]))
    print("text_layer_chars=%d emitted_chars=%d char_recall=%s" % (
        st["text_layer_chars"], st["emitted_chars"], st["char_recall"]))
    print("selfcheck: %s (%d errors, %d warnings)" % (
        "OK" if chk["ok"] else "FAILED", len(chk["errors"]), len(chk["warnings"])))
    if st["text_layer_chars"] == 0:
        print("NOTE: no text layer on any parsed page -> scanned document; "
              "use the OCR/vision path described in SKILL.md")
        return 3
    return 0 if chk["ok"] else 4


if __name__ == "__main__":
    sys.exit(main())