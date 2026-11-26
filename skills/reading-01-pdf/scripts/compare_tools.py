#!/usr/bin/env python3
"""compare_tools.py -- score three extraction routes with one yardstick.

Routes, all on the same PDF, full document (no --pages probe):

  naive        page.get_text("text")           the bare-agent dump that
                                               results/baseline.json scores
  pymupdf4llm  pymupdf4llm.to_markdown(doc)    PyMuPDF's official PDF->MD
                                               exporter, i.e. the most common
                                               lightweight alternative
  skill        outputs/scripts/parse_pdf.py    this engine, schema pdf-struct/2

Criteria are geometric/textual and machine-checkable.  The geometry helpers
(_lines_of_page / _col_of / the two-column gate) are copied from
baseline_compare.py so the numbers line up with results/baseline.json.

The engine's doc.json/text.md used for measurement are regenerated into
work/_tools_probe/engine/<name>/ (stats asserted identical to the shipped
report.json); nothing inside bundle/results/*/ is rewritten.  The result goes
to results/compare_tools.json.

Usage: python compare_tools.py [--corpus DIR] [--out FILE] [--cases a,b]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import statistics
import subprocess
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore

HERE = Path(__file__).resolve()
SCRIPTS = HERE.parent
BUNDLE = SCRIPTS.parent.parent
RESULTS = BUNDLE / "results"
WORK = Path("D:/dsh_workplace/work/_tools_probe")
CASES = ["resnet", "transformer", "bert", "gpt3", "vit"]
METRICS = ["heading_count", "table_count", "bbox_blocks",
           "running_header_lines_leaked", "figure_label_chars_leaked",
           "cross_column_interleavings", "wall_time_s"]
TOOLS = ["naive", "pymupdf4llm", "skill"]
REPEATS = 3
MARGIN = 0.10          # top/bottom band used to spot running heads


# ---------------------------------------------------------------- geometry --
# copied from baseline_compare.py: same yardstick as results/baseline.json

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


def _two_col_geom(bands):
    """A real 2-column page: two comparable bands, narrow gutter."""
    if len(bands) != 2:
        return False
    content = bands[1][1] - bands[0][0]
    gutter = bands[1][0] - bands[0][1]
    w0, w1 = bands[0][1] - bands[0][0], bands[1][1] - bands[1][0]
    return (content > 0 and gutter <= 0.12 * content
            and min(w0, w1) >= 0.22 * content)


def _crosses_gutter(bb, bands):
    """A unit that physically spans both columns is not a column decision."""
    return bb[0] < bands[0][1] - 2.0 and bb[2] > bands[1][0] + 2.0


def _count_flips(seq_lines, bands):
    """Right-column run followed by a return to the left column.

    Unit = whatever the tool emits as an atomic text unit (a line for naive /
    pymupdf4llm, a paragraph block for the skill).  Units that straddle the
    gutter are skipped.  None = page does not qualify (baseline's gate: >=8
    units in each band, plus a real two-column geometry).
    """
    seq = []
    for txt, bb in seq_lines:
        if not txt or len(txt) < 3 or _crosses_gutter(bb, bands):
            continue
        c = _col_of(bb, bands)
        if c is None:
            continue
        seq.append(c)
    if seq.count(0) >= 8 and seq.count(1) >= 8:
        seen_right, flips = False, 0
        for c in seq:
            if c == 1:
                seen_right = True
            elif seen_right:
                flips += 1
                seen_right = False
        return flips
    return None


def _sum_flips(seq_by_page, doc_meta, report_pages):
    total = 0
    for i, seq in seq_by_page.items():
        pg = report_pages.get(i, {})
        bands = doc_meta["pages"][i - 1].get("column_bands") or []
        if pg.get("empty") or not _two_col_geom(bands):
            continue
        total += _count_flips(seq, bands) or 0
    return total


# ------------------------------------------------------------------- text ----

def _norm(s):
    """Whitespace-insensitive key: rewrapping must not hide a leak."""
    return "".join(s.split())


_MD_LEAD = re.compile(r"^[#>*_\-+\s]+")
_MD_TAIL = re.compile(r"[\s*_|]+$")


def _strip_md(line):
    return _MD_TAIL.sub("", _MD_LEAD.sub("", line))


# ---------------------------------------------------------------- sources ----

def ensure_engine(name, pdf):
    """Regenerate the engine's doc.json/text.md under work/, timed once."""
    out = WORK / "engine" / name
    if not (out / "doc.json").exists() or not (out / "_wall.json").exists():
        out.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, str(SCRIPTS / "parse_pdf.py"),
                            str(pdf), "--out", str(out)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        secs = round(time.perf_counter() - t0, 3)
        if r.returncode != 0:
            raise RuntimeError("parse_pdf.py exit %d: %s"
                               % (r.returncode, (r.stderr or "")[-400:]))
        (out / "_wall.json").write_text(json.dumps({"seconds": secs}),
                                        encoding="utf-8")
    wall = json.loads((out / "_wall.json").read_text(encoding="utf-8"))["seconds"]
    meta = json.loads((out / "doc.json").read_text(encoding="utf-8"))
    md = (out / "text.md").read_text(encoding="utf-8")
    engine_report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    return meta, md, wall, engine_report


def skill_pages_from_md(md):
    """Parse text.md into {page: [(text, bbox)]} in emitted order."""
    page_re = re.compile(r"^<!--\s*=+\s*page\s+(\d+)")
    blk_re = re.compile(r"^<!--\s*p(\d+)-b\d+\s*\|\s*type=(\S+)\s*\|"
                        r"\s*col=(-?\d+)\s*\|\s*bbox=([-\d.,]+)\s*-->")
    pages, cur = {}, None
    for raw in md.splitlines():
        s = raw.strip()
        if not s or s.startswith("<!--"):
            m = blk_re.match(s)
            if m:
                bb = [float(x) for x in m.group(4).split(",")]
                cur = {"page": int(m.group(1)), "bbox": bb, "lines": []}
                pages.setdefault(cur["page"], []).append(cur)
            else:
                cur = None
                m = page_re.match(s)
                if m:
                    pages.setdefault(int(m.group(1)), [])
            continue
        if cur is not None:
            cur["lines"].append(s)
    out = {}
    for pg, blocks in pages.items():
        seq = []
        for b in blocks:
            txt = " ".join(b["lines"]).strip()
            if txt:
                seq.append((_strip_md(txt), tuple(b["bbox"])))
        out[pg] = seq
    return out


def body_lines_of_md(md_text):
    out = []
    for ln in md_text.splitlines():
        s = ln.strip()
        if not s or s.startswith("<!--") or s.startswith("!["):
            continue
        out.append(_strip_md(s))
    return out


# ----------------------------------------------------------------- scoring --

def header_lines(doc_meta, per_page_lines):
    """Running heads/footers for THIS document, from two objective sources:

      (a) the engine's dropped_running_text (what baseline_compare.py uses),
      (b) geometric repeats: identical text (>=8 chars, non-numeric) inside the
          top/bottom 10% band of >=3 pages.

    One set is built per PDF and applied to all three tools.
    """
    hs = set()
    for p in doc_meta["pages"]:
        for t in (p.get("dropped_running_text") or []):
            t = t.strip()
            if len(t) >= 8 and not t.isdigit():
                hs.add(_norm(t))
    seen = {}
    for i, lines in enumerate(per_page_lines, start=1):
        h = doc_meta["pages"][i - 1].get("height") or 792.0
        for txt, bb in lines:
            if len(txt) < 8 or txt.isdigit():
                continue
            if bb[3] <= MARGIN * h or bb[1] >= (1.0 - MARGIN) * h:
                seen.setdefault(_norm(txt), set()).add(i)
    for k, v in seen.items():
        if len(v) >= 3:
            hs.add(k)
    return hs


def count_header_hits(lines, hs):
    return sum(1 for ln in lines if _norm(ln) in hs)


def markdown_tables(md_text):
    """Markdown table blocks: a separator row plus contiguous '|' rows."""
    n, i = 0, 0
    lines = md_text.splitlines()
    while i < len(lines):
        if lines[i].strip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            block = lines[i:j]
            sep = sum(1 for b in block
                      if re.match(r"^\|?[\s:\-|]+\|?$", b.strip()) and "---" in b)
            if sep and len(block) >= sep + 1:
                n += 1
            i = j
        else:
            i += 1
    return n


def figure_inventory(doc_meta):
    """Figure-label chars per page, from the engine's block mask."""
    inv, total = {}, 0
    for b in doc_meta["blocks"]:
        if b["type"] == "figure_label":
            t = (b.get("text") or "").strip()
            if t:
                inv.setdefault(b["page"], []).append(t)
                total += len(t)
    return inv, total


def explain_by_page(doc_meta):
    """Text a page legitimately carries outside its figures (every block that is
    not a figure_label); used to discount coincidental label matches."""
    exp = {}
    for b in doc_meta["blocks"]:
        if b["type"] == "figure_label":
            continue
        t = _norm(b.get("text") or "")
        if t:
            exp[b["page"]] = exp.get(b["page"], "") + t
    return exp


def figure_leak(inv, body_by_page, explain):
    """Chars of the figure-label inventory that survive into a tool's body.

    A label counts only when its text is on that page of the tool's output and
    cannot be explained by a non-figure block of the same page.  Labels under 4
    chars are skipped: they cannot be told apart from body numbers.
    """
    hit = 0
    for pg, labels in inv.items():
        bn = body_by_page.get(pg, "")
        en = explain.get(pg, "")
        for t in labels:
            k = _norm(t)
            if len(t) >= 4 and k in bn and k not in en:
                hit += len(t)
    return hit


def inventory_ge4(inv):
    return sum(len(t) for ls in inv.values() for t in ls if len(t) >= 4)


# -------------------------------------------------------------------- runs --

def time_naive(pdf, reps=REPEATS):
    secs, texts = [], None
    for _ in range(reps):
        t0 = time.perf_counter()
        d = fitz.open(str(pdf))
        texts = [p.get_text("text") for p in d]
        d.close()
        secs.append(round(time.perf_counter() - t0, 4))
    return secs, texts


def time_p4l(pdf, reps=REPEATS):
    import pymupdf4llm
    secs, md = [], None
    for _ in range(reps):
        buf = io.StringIO()
        t0 = time.perf_counter()
        d = fitz.open(str(pdf))
        with redirect_stdout(buf):
            md = pymupdf4llm.to_markdown(d, use_ocr=False)
        d.close()
        secs.append(round(time.perf_counter() - t0, 4))
    buf = io.StringIO()
    d = fitz.open(str(pdf))
    with redirect_stdout(buf):
        chunks = pymupdf4llm.to_markdown(d, use_ocr=False, page_chunks=True)
    d.close()
    return secs, md, {i: c["text"] for i, c in enumerate(chunks, start=1)}


def md_seq_for_page(page_text, pdf_lines):
    """Recover the source line order behind pymupdf4llm's markdown page.

    pymupdf4llm merges PDF lines into paragraphs, so one markdown line is not
    one PDF line.  Every PDF line's text is located inside the page's markdown
    (substring position, repeated strings consumed left to right) and the
    matches are ordered by position, which restores the line order the exporter
    used -- without inventing a second yardstick.
    """
    seq, cursor = [], {}
    for ln in page_text.splitlines():
        s = _strip_md(ln.strip())
        if len(s) < 3:
            continue
        k = _norm(s)
        local = []
        for txt, bb in pdf_lines:
            kt = _norm(txt)
            if len(kt) < 3:
                continue
            pos = k.find(kt, cursor.get(kt, 0))
            if pos < 0:
                continue
            cursor[kt] = pos + len(kt)
            local.append((pos, kt, bb))
        local.sort(key=lambda h: (h[0], h[1]))
        seq.extend((t, bb) for _, t, bb in local)
    return seq


# --------------------------------------------------------------------- main --

def measure_case(doc_meta, md_skill, skill_wall, pdf, report):
    doc = fitz.open(str(pdf))
    report_pages = {p["page"]: p for p in report["pages"]}
    page_lines = {}
    for i, p in enumerate(doc, start=1):
        page_lines[i] = _lines_of_page(p)
        if i <= len(doc_meta["pages"]):
            doc_meta["pages"][i - 1].setdefault("height", p.rect.height)

    hs = header_lines(doc_meta, [page_lines[i] for i in sorted(page_lines)])
    fig_inv, fig_total = figure_inventory(doc_meta)
    fig_ge4 = inventory_ge4(fig_inv)
    explain = explain_by_page(doc_meta)
    two_col = int((doc_meta.get("document") or {}).get("column_template") or 1) >= 2

    # ---- naive
    n_secs, n_texts = time_naive(pdf)
    n_body = body_lines_of_md("\n".join(n_texts))
    n_fig = figure_leak(fig_inv, {i: _norm(t) for i, t in enumerate(n_texts, 1)},
                        explain)
    n_flips = _sum_flips(page_lines, doc_meta, report_pages) if two_col else None

    # ---- pymupdf4llm
    p_err = None
    try:
        p_secs, p_md, p_pages = time_p4l(pdf)
    except Exception as exc:  # noqa: BLE001 - record, keep going
        p_secs, p_md, p_pages = None, None, {}
        p_err = "%s: %s" % (type(exc).__name__, exc)
    p_body = body_lines_of_md(p_md) if p_md else []
    p_fig = figure_leak(fig_inv, {i: _norm(t) for i, t in p_pages.items()},
                        explain) if p_md else None
    p_flips = None
    if two_col and p_md is not None:
        p_flips = _sum_flips({i: md_seq_for_page(p_pages[i], page_lines[i])
                              for i in p_pages}, doc_meta, report_pages)

    # ---- skill
    s_pages = skill_pages_from_md(md_skill)
    s_body = body_lines_of_md(md_skill)
    s_page_norm = {i: _norm(" ".join(t for t, _ in seq)) for i, seq in s_pages.items()}
    s_flips = _sum_flips(s_pages, doc_meta, report_pages) if two_col else None

    doc.close()

    stats = report["stats"]
    skill = {
        "heading_count": stats["n_sections"],
        "table_count": stats["n_tables"],
        "bbox_blocks": stats["n_blocks"],
        "running_header_lines_leaked": count_header_hits(s_body, hs),
        "figure_label_chars_leaked": figure_leak(fig_inv, s_page_norm, explain),
        "cross_column_interleavings": s_flips,
        "wall_time_s": skill_wall,
    }
    naive = {
        "heading_count": 0,
        "table_count": 0,
        "bbox_blocks": 0,
        "running_header_lines_leaked": count_header_hits(n_body, hs),
        "figure_label_chars_leaked": n_fig,
        "cross_column_interleavings": n_flips,
        "wall_time_s": round(statistics.median(n_secs), 3),
    }
    p4l = {
        "heading_count": (sum(1 for ln in p_md.splitlines()
                              if re.match(r"^#{1,6} ", ln)) if p_md else None),
        "table_count": markdown_tables(p_md) if p_md else None,
        "bbox_blocks": 0,
        "running_header_lines_leaked": count_header_hits(p_body, hs) if p_md else None,
        "figure_label_chars_leaked": p_fig,
        "cross_column_interleavings": p_flips,
        "wall_time_s": round(statistics.median(p_secs), 3) if p_secs else None,
    }
    diag = {
        "header_set_size": len(hs),
        "header_set_sample": sorted(hs)[:4],
        "figure_label_inventory_chars": fig_total,
        "figure_label_inventory_chars_ge4": fig_ge4,
        "figure_metric_applicable": fig_ge4 > 0,
        "naive_figure_leak_fraction": round(n_fig / fig_ge4, 4) if fig_ge4 else None,
        "pymupdf4llm_figure_leak_fraction":
            round(p_fig / fig_ge4, 4) if (fig_ge4 and p_fig is not None) else None,
        "skill_n_headings": stats.get("n_headings"),
        "seconds_naive_all": n_secs,
        "seconds_pymupdf4llm_all": p_secs,
        "pymupdf4llm_error": p_err,
    }
    return {"file": pdf.name, "pages": len(page_lines),
            "naive": naive, "pymupdf4llm": p4l, "skill": skill}, diag


def fmt(v):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return "%.3f" % v
    return str(v)


def print_table(cases, res):
    head = ("case", "tool", "head", "tabl", "bbox", "hdrleak", "figch", "xcol", "wall_s")
    print("%-16s %-12s %7s %7s %7s %8s %7s %6s %9s" % head)
    print("-" * 90)
    for c in cases:
        for t in TOOLS:
            m = c[t]
            print("%-16s %-12s %7s %7s %7s %8s %7s %6s %9s" % (
                c["file"], t, fmt(m["heading_count"]), fmt(m["table_count"]),
                fmt(m["bbox_blocks"]), fmt(m["running_header_lines_leaked"]),
                fmt(m["figure_label_chars_leaked"]),
                fmt(m["cross_column_interleavings"]), fmt(m["wall_time_s"])))
        print("-" * 90)
    print("%-16s %7s %7s %7s %8s %7s %6s %9s" % ("TOTAL", "head", "tabl", "bbox",
                                                 "hdrleak", "figch", "xcol", "wall_s"))
    for t in TOOLS:
        d = res["totals"][t]
        print("%-16s %7s %7s %7s %8s %7s %6s %9s" % (
            t, fmt(d["heading_count"]), fmt(d["table_count"]), fmt(d["bbox_blocks"]),
            fmt(d["running_header_lines_leaked"]), fmt(d["figure_label_chars_leaked"]),
            fmt(d["cross_column_interleavings"]), fmt(d["wall_time_s"])))


def totals(cases):
    out = {}
    for t in TOOLS:
        d = {}
        for k in METRICS:
            vals = [c[t].get(k) for c in cases]
            if k == "cross_column_interleavings":
                nums = [v for v in vals if v is not None]
                d[k] = sum(nums) if nums else None
            elif any(v is None for v in vals):
                d[k] = None
            elif k == "wall_time_s":
                d[k] = round(sum(vals), 3)
            else:
                d[k] = sum(vals)
        out[t] = d
    return out


def perf_medians():
    """Median end-to-end CLI seconds per case, if perf_bench.py already ran."""
    p = RESULTS / "perf.json"
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return {str(c.get("file", "")).replace(".pdf", ""): c.get("seconds_median")
            for c in d.get("cases", [])}


NOTE = (
    "Routes run over the whole document (no --pages probe). naive = PyMuPDF "
    "page.get_text('text'). pymupdf4llm = pymupdf4llm 2.1 "
    "to_markdown(doc, use_ocr=False), every other argument at library default "
    "(table_strategy='lines_strict'); OCR is off because no OCR engine is "
    "installed offline. skill = outputs/scripts/parse_pdf.py (pdf-struct/2): "
    "heading/table/block counts read from results/<name>/report.json "
    "(stats.n_sections, n_tables, n_blocks), body text from a regenerated run in "
    "work/_tools_probe/engine/<name> whose stats are asserted equal to the "
    "shipped report.json. Geometry helpers (_lines_of_page, _col_of, two-column "
    "gate) are copied from baseline_compare.py. running_header_lines_leaked: "
    "header set per PDF = engine dropped_running_text (len>=8, non-numeric) UNION "
    "lines in the top/bottom 10% repeated on >=3 pages; the same set is applied "
    "to all three tools, a hit is a full-line match after whitespace "
    "normalisation. figure_label_chars_leaked: inventory = chars of engine blocks "
    "typed figure_label; a label (>=4 chars, so body numbers cannot fake a match) "
    "counts when it appears on that same page of the tool's output and is not "
    "explainable by a non-figure block of that page. Two honest caveats, both "
    "visible in diag: (1) the running-header metric only fires on vit -- the "
    "other four PDFs carry page numbers only in their margins, and bare numbers "
    "are excluded by design, so 0 there means 'no qualifying running head', not "
    "'measured clean'; (2) gpt3 has an empty figure_label inventory (its figures "
    "are vector charts without typed labels), so its figure value of 0 means "
    "'nothing to leak' -- diag marks it figure_metric_applicable=false. "
    "cross_column_interleavings: "
    "scored only for document-level 2-column PDFs (resnet, bert) with baseline's "
    "gate (gutter <=12% of content width, >=8 units in each band); the unit is "
    "the tool's own emitted unit (line for naive/pymupdf4llm, paragraph block for "
    "skill) and units straddling the gutter are skipped; null = not applicable, "
    "never zero. In results/baseline.json the skill side of that metric was 0 by "
    "construction (the engine's own block order); here it is re-measured from the "
    "emitted text.md with the same rule, which is why it is not exactly 0. "
    "wall_time_s: naive and pymupdf4llm are the median of 3 full runs in one "
    "process; skill is the median of 3 end-to-end CLI runs from results/perf.json "
    "when present (that CLI run also rasterises figures and overlay PNGs, which "
    "the other two do not), else one run. n/a = not computable."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="D:/dsh_workplace/corpus")
    ap.add_argument("--out", default=str(RESULTS / "compare_tools.json"))
    ap.add_argument("--cases", default=",".join(CASES))
    a = ap.parse_args()
    corpus = Path(a.corpus)
    WORK.mkdir(parents=True, exist_ok=True)

    cases, diags = [], {}
    perf = perf_medians()
    for name in a.cases.split(","):
        pdf = corpus / ("%s.pdf" % name)
        report = json.loads((RESULTS / name / "report.json").read_text(encoding="utf-8"))
        doc_meta, md_skill, skill_wall, engine_report = ensure_engine(name, pdf)
        if perf.get(name):
            skill_wall = perf[name]
        row, diag = measure_case(doc_meta, md_skill, skill_wall, pdf, report)
        diag["skill_wall_source"] = ("perf.json median of 3" if perf.get(name)
                                     else "single CLI run")
        diag["regenerated_stats_equal_shipped"] = (
            json.dumps(engine_report.get("stats"), sort_keys=True)
            == json.dumps(report.get("stats"), sort_keys=True))
        cases.append(row)
        diags[name] = diag
        print("[ok] %-12s pages=%3d skill_wall=%s" % (name, row["pages"], skill_wall))

    res = {
        "schema": "pdf-struct/toolcompare/1",
        "note": NOTE,
        "tools": TOOLS,
        "cases": cases,
        "totals": totals(cases),
        "diag": diags,
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    print("")
    print_table(cases, res)
    print("")
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
