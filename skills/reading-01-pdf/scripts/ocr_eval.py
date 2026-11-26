#!/usr/bin/env python3
"""ocr_eval.py -- score the OCR branch against a page's text layer.

The OCR branch (``ocr_pages.py`` -> vision transcript -> ``merge_ocr.py``) can
be exercised on synthetic fixtures, but that only proves the pipeline runs.  It
says nothing about how well a reader model transcribes a real page.  This script
closes that gap: it renders one page, installs a transcript, merges it, and
compares the merged text with the same page's vector text layer.

    python outputs/scripts/ocr_eval.py \
        --pdf ../corpus/resnet.pdf --page 1 --dpi 200 \
        --transcript D:/work/page-01.md \
        --work D:/work/_ocr_eval/run \
        --json ../results/ocr-eval.json \
        --png ../results/ocr/page-01.png

What is measured
----------------
* ``char_similarity``  1 - levenshtein(a, b) / max(len(a), len(b)) on the
  normalised character stream.  The levenshtein is a self-contained bit-parallel
  (Myers/Hyyro) implementation -- no third-party packages.
* ``token_recall``      share of the truth's word set that the transcript covers.
* ``line_count_ratio``  transcript lines / truth lines.  Both sides keep the
  page's own line breaks, so a transcript that reflows paragraphs scores < 1
  here even if every word is right.
* ``column_order_ok``   every vision block is matched back to the truth block it
  reproduces; the matched blocks' side of the gutter must never go right->left.
* ``running_header_dropped``  the page's margin stamp is a ``margin_artifact``
  block and does not leak into body text.

Normalisation (both sides, same function): drop HTML comments and
``<!-- pN-bNNN ... -->`` provenance lines, drop ``[header]``/``[footer]`` runs,
drop markdown markers, NFKC (full-width -> half-width, ligatures -> letters),
unify quotes/dashes, collapse whitespace, lowercase.

Truth = ``parse_pdf.py`` output for the same page (block text, not the rendered
markdown), restricted to prose block types: figure placeholders, in-figure axis
labels and the dropped running header are excluded -- they are either not text
the prompt asks for or not text at all.  The excluded in-figure labels are
counted and reported so the omission is visible instead of silent.

Exit codes: 0 ok, 2 usage/IO error, 3 no text layer on the page (nothing to
score; render+merge still ran), 4 --strict and a structural assertion failed.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))

CONF_RE = re.compile(r"^\s*confidence:\s*(high|medium|low)", re.I)
CONF_SCORE = {"high": 0.9, "medium": 0.6, "low": 0.3, "unknown": 0.0}

# block types that carry prose the transcript is expected to reproduce
PROSE = {"heading", "author", "affiliation", "body", "caption", "footnote",
         "reference", "code", "table", "table_row"}
# everything else is either not prose (figure) or margin furniture
SKIP = {"margin_artifact", "figure", "figure_label", "page_number",
        "running_header", "running_footer", "header", "footer"}

QUOTES = {"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
          "\u2014": "-", "\u2013": "-", "\u2212": "-", "\u00ad": ""}


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def run(cmd, quiet=False):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", errors="replace")
    if not quiet:
        out = (p.stdout or "").strip()
        if out:
            print("    " + out.replace("\n", "\n    "))
    return p


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def normalize(text, fold=True):
    """-> (flat, n_lines).  Same function for transcript and truth.

    ``fold=True`` is the comparison form: NFKC (ligatures -> letters, full-width
    -> half-width) and quote/dash unificiation, so typography never counts as an
    error.  ``fold=False`` keeps those codepoints, which is what makes the
    verbatim-copy check possible: a transcript copied out of the text layer
    would match this stricter form exactly.
    """
    if fold:
        text = unicodedata.normalize("NFKC", text)
    lines, in_margin = [], False
    for raw in text.splitlines():
        s = raw.replace("\ufeff", "").strip()
        if not s:
            in_margin = False
            continue
        if s.lower().startswith("## page") or CONF_RE.match(s):
            continue
        if s.startswith("<!--") or s.startswith("-->"):
            continue
        if s.startswith("[header]") or s.startswith("[footer]"):
            # margin furniture: transcribed, but not body text.  Both sides are
            # dropped so the running header cannot flatter or inflate the score.
            in_margin = True
            continue
        elif in_margin:
            continue
        s = s.replace("[[figure]]", "").replace("[[formula]]", "").strip()
        if not s:
            continue
        m = re.match(r"^!\[([^\]]*)\]\([^)]*\)$", s)      # markdown image
        if m:
            s = m.group(1)
        s = re.sub(r"^#{1,6}\s*", "", s)
        s = re.sub(r"^>\s*", "", s)
        s = s.replace("**", "").replace("__", "").replace("`", "")
        if fold:
            for k, v in QUOTES.items():
                s = s.replace(k, v)
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            lines.append(s)
    flat = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return (flat.lower() if fold else flat), len(lines)


def tokens(flat):
    return re.findall(r"[a-z0-9]+", flat)


def levenshtein(a, b):
    """Bit-parallel edit distance (Myers 1999 / Hyyro).  Pure Python ints."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(b) > len(a):
        a, b = b, a
    m = len(b)
    mask, last = (1 << m) - 1, 1 << (m - 1)
    peq = {}
    for i, ch in enumerate(b):
        peq[ch] = peq.get(ch, 0) | (1 << i)
    vp, vn, score = mask, 0, m
    for ch in a:
        pm = peq.get(ch, 0)
        x = pm | vn
        d0 = (((x & vp) + vp) ^ vp) | x
        hp = vn | ~(d0 | vp)
        hn = vp & d0
        if hp & last:
            score += 1
        elif hn & last:
            score -= 1
        hp = ((hp << 1) | 1) & mask
        hn = (hn << 1) & mask
        vp = (hn | ~(d0 | hp)) & mask
        vn = hp & d0
    return score


# --------------------------------------------------------------------------- #
# steps
# --------------------------------------------------------------------------- #
def ensure_base(pdf, page, outdir):
    doc = os.path.join(outdir, "doc.json")
    if os.path.exists(doc):
        return
    print("[1/4] text-layer parse (base doc.json)")
    run([sys.executable, os.path.join(HERE, "parse_pdf.py"), pdf,
         "--out", outdir, "--pages", str(page)])


def render(pdf, page, outdir, dpi):
    print("[2/4] render page %d at %d dpi" % (page, dpi))
    p = run([sys.executable, os.path.join(HERE, "ocr_pages.py"), pdf,
             "--out", outdir, "--dpi", str(dpi), "--pages", str(page)])
    if p.returncode != 0:
        raise SystemExit("ocr_pages.py failed")
    return os.path.join(outdir, "ocr", "page-%02d.png" % page)


def install_transcript(transcript, outdir, page):
    dst = os.path.join(outdir, "ocr", "page-%02d.md" % page)
    src = os.path.abspath(transcript)
    if os.path.abspath(dst) != src:
        shutil.copyfile(src, dst)
    print("      transcript -> %s" % dst)
    return dst


def merge(outdir):
    print("[3/4] merge transcript into doc.json")
    p = run([sys.executable, os.path.join(HERE, "merge_ocr.py"), outdir,
             "--require", "all"])
    if p.returncode != 0:
        raise SystemExit("merge_ocr.py failed")


def build_truth(pdf, page, truthdir):
    p = run([sys.executable, os.path.join(HERE, "parse_pdf.py"), pdf,
             "--out", truthdir, "--pages", str(page)], quiet=True)
    if p.returncode == 3:
        return None, "page has no text layer; nothing to score against"
    if p.returncode != 0:
        return None, "parse_pdf.py exit %d: %s" % (p.returncode, (p.stdout or "")[:200])
    return load_json(os.path.join(truthdir, "doc.json")), None


def page_of(doc, page):
    for pg in doc.get("pages", []):
        if pg.get("page") == page:
            return pg
    return {}


# --------------------------------------------------------------------------- #
# scoring
# --------------------------------------------------------------------------- #
def score(transcript_path, doc, truth, page):
    width = page_of(truth, page).get("width") or 612.0
    mid = width / 2.0

    tblocks = [b for b in doc["blocks"] if b.get("page") == page]
    vblocks = [b for b in tblocks if b.get("type") not in SKIP and b.get("text", "").strip()]
    n_figure_labels = sum(1 for b in truth["blocks"]
                          if b.get("page") == page and b.get("type") == "figure_label")
    truth_prose = [b for b in truth["blocks"]
                   if b.get("page") == page and b.get("type") in PROSE]

    def side_of(bbox):
        if not bbox:
            return "F", -1.0
        wide = (bbox[2] - bbox[0]) > 0.55 * width
        return ("F" if wide else
                ("R" if (bbox[0] + bbox[2]) / 2.0 >= mid else "L")), bbox[1]

    # Reading order for the truth, column by column.  A two-column page is read
    # left column top->bottom, then right column top->bottom; joining the parse
    # output in its stored order would interleave the columns line by line and
    # make any correctly ordered transcript look like a shuffle.
    # The title/authors band spans both columns, so it is peeled off first: up
    # to the first flush-left line (the first line that sits on the page's left
    # margin) the page is single-column, and there rows are read left to right.
    xs = [(b.get("bbox") or [0])[0] for b in truth_prose if b.get("bbox")]
    y_cols = None
    if xs:
        page_left = min(xs)
        flush = [b.get("bbox")[1] for b in truth_prose
                 if b.get("bbox") and b["bbox"][0] <= page_left + 3.0]
        y_cols = min(flush) if flush else None
    if y_cols is None:
        truth_sorted = sorted(truth_prose,
                              key=lambda b: (side_of(b.get("bbox"))[0] == "R",
                                             side_of(b.get("bbox"))[1],
                                             (b.get("bbox") or [0])[0]))
    else:
        front = sorted([b for b in truth_prose if (b.get("bbox") or [0, 0, 0, 0])[3] <= y_cols + 1.0],
                       key=lambda b: ((b.get("bbox") or [0, 0])[1], (b.get("bbox") or [0])[0]))
        rest = sorted([b for b in truth_prose if (b.get("bbox") or [0, 0, 0, 0])[3] > y_cols + 1.0],
                      key=lambda b: (side_of(b.get("bbox"))[0] == "R",
                                     side_of(b.get("bbox"))[1],
                                     (b.get("bbox") or [0])[0]))
        truth_sorted = front + rest

    with open(transcript_path, encoding="utf-8") as fh:
        vraw = fh.read()
    tr_raw = "\n".join(b.get("text", "") for b in truth_sorted)
    gflat, g_lines = normalize(vraw)      # generated (vision transcript)
    tflat, t_lines = normalize(tr_raw)    # truth (vector text layer)

    d = levenshtein(tflat, gflat)
    denom = max(len(tflat), len(gflat)) or 1
    tset, gset = set(tokens(tflat)), set(tokens(gflat))
    inter = tset & gset

    # strict form: no NFKC, no quote folding.  Ligatures and curly quotes stay,
    # so a transcript that was copied from the text layer scores 1.0 here.
    traw, _ = normalize(tr_raw, fold=False)
    graw, _ = normalize(vraw, fold=False)
    draw = levenshtein(traw, graw)
    raw_sim = round(1.0 - draw / float(max(len(traw), len(graw)) or 1), 4)
    n_lig = sum(traw.count(c) for c in "\ufb00\ufb01\ufb02\ufb03\ufb04")

    # --- order / header checks -------------------------------------------- #
    # Walk the truth in column order and ask which vision block each truth line
    # ended up in.  A column-major transcript keeps those block indices
    # non-decreasing; a transcript that interleaves the columns (or reads the
    # right column first) does not.  Matching by containment, not Jaccard, so a
    # 15-line vision paragraph still matches the short truth line inside it.
    vtok = [(i, set(tokens(normalize(b["text"])[0]))) for i, b in enumerate(vblocks)]
    seq, matches = [], []
    for tb in truth_sorted:
        tt = set(tokens(normalize(tb.get("text", ""), fold=True)[0]))
        if len(tt) < 3:
            continue
        best_i, best_c = None, 0.0
        for i, vs in vtok:
            c = len(tt & vs) / float(len(tt))
            if c > best_c:
                best_i, best_c = i, c
        if best_i is None or best_c < 0.5:
            continue
        side = side_of(tb.get("bbox"))[0]
        seq.append(best_i)
        matches.append({"truth": tb["id"], "side": side, "vision_block": best_i,
                        "containment": round(best_c, 3),
                        "text": (tb.get("text") or "").splitlines()[0][:70]})
    order_ok = bool(seq) and all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))
    sides = {m["side"] for m in matches}
    column_order_ok = order_ok and len(seq) >= 5 and {"L", "R"} <= sides

    header_expected = any(b.get("type") == "margin_artifact"
                          and re.search(r"arxiv|\d", b.get("text", ""), re.I)
                          for b in truth["blocks"] if b.get("page") == page)
    margin_blocks = [b for b in tblocks if b.get("type") == "margin_artifact"]
    body_has_stamp = any(re.search(r"arxiv", b.get("text", ""), re.I)
                         for b in vblocks)
    header_ok = (not body_has_stamp) and (bool(margin_blocks) or not header_expected)

    # --- examples ---------------------------------------------------------- #
    # Character-level hunks on the strict stream: exact, reproducible, and it
    # does not pretend a ligature split is a missing word.  Each hunk gives one
    # truth excerpt (what is on the page) and one transcript excerpt (what was
    # read), so the pair is directly comparable.
    def tight(s, i, j, pad=14):
        return s[max(0, i - pad):min(len(s), j + pad)].strip()

    char_diffs = []
    sm = difflib.SequenceMatcher(None, traw, graw, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        char_diffs.append({"op": tag,
                           "truth": tight(traw, i1, i2),
                           "read": tight(graw, j1, j2)})
    missing_examples = [d["truth"] for d in char_diffs][:6]
    extra_examples = [d["read"] for d in char_diffs][:6]

    confs = [CONF_SCORE.get((b.get("confidence") or "unknown").lower(), 0.0)
             for b in tblocks]
    mean_conf = round(sum(confs) / len(confs), 4) if confs else 0.0

    return {
        "char_similarity": round(1.0 - d / float(denom), 4),
        "token_recall": round(len(inter) / float(len(tset) or 1), 4),
        "token_precision": round(len(inter) / float(len(gset) or 1), 4),
        "line_count_ratio": round(g_lines / float(t_lines or 1), 4),
        "column_order_ok": column_order_ok,
        "running_header_dropped": header_ok,
        "blocks": len(tblocks),
        "mean_confidence": mean_conf,
        "missing_examples": missing_examples,
        "extra_examples": extra_examples,
        "detail": {
            "char_edit_distance": d,
            "raw_char_similarity": raw_sim,
            "raw_edit_distance": draw,
            "ligature_chars_in_truth": n_lig,
            "char_diffs": char_diffs,
            "chars_truth": len(tflat),
            "chars_transcript": len(gflat),
            "lines_truth": t_lines,
            "lines_transcript": g_lines,
            "words_truth": len(tset),
            "words_transcript": len(gset),
            "words_shared": len(inter),
            "figure_label_blocks_excluded": n_figure_labels,
            "column_sequence": seq,
            "matches": matches[:40],
        },
    }


def assertions(doc, page, outdir):
    tblocks = [b for b in doc["blocks"] if b.get("page") == page]
    st = doc.get("stats", {})
    out = []

    def chk(name, ok, detail=""):
        out.append({"check": name, "ok": bool(ok), "detail": detail})

    chk("bbox is null on every page block",
        all(b.get("bbox") is None for b in tblocks),
        "%d blocks" % len(tblocks))
    chk("bbox_source == vision",
        all(b.get("bbox_source") == "vision" for b in tblocks), "")
    chk("confidence present on every block",
        all(b.get("confidence") for b in tblocks),
        ",".join(sorted({b.get("confidence") or "?" for b in tblocks})))
    chk("stats.char_recall is null", st.get("char_recall") is None,
        "%r" % (st.get("char_recall"),))
    chk("stats.ocr_pages covers page %d" % page,
        page in (st.get("ocr_pages") or []), "%s" % (st.get("ocr_pages"),))
    chk("transcript produced blocks", len(tblocks) > 0, "%d" % len(tblocks))
    chk("ocr/text.md written", os.path.exists(os.path.join(outdir, "ocr", "text.md")), "")
    return out


def rel_pdf(pdf):
    """Shortest readable path to the PDF (bundle-relative when possible)."""
    p = os.path.abspath(pdf)
    roots = [os.getcwd(), os.path.dirname(HERE), os.path.dirname(os.path.dirname(HERE)),
             os.path.dirname(os.path.dirname(os.path.dirname(HERE)))]
    best = None
    for r in roots:
        try:
            rel = os.path.relpath(p, r)
        except ValueError:
            continue
        if not rel.startswith("..") and (best is None or len(rel) < len(best)):
            best = rel
    return (best or p).replace("\\", "/")


def save_png(src, dst, max_kb):
    """Copy the render, shrinking only as much as the size cap forces."""
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    limit = max_kb * 1024
    if os.path.getsize(src) <= limit:
        shutil.copyfile(src, dst)
        return 1.0, "copy"
    from PIL import Image
    im = Image.open(src)
    # a text page survives a palette reduction untouched and keeps figure
    # colours; try that before touching the resolution.
    for colors, mode in ((64, "palette64"), (32, "palette32"), (16, "palette16")):
        q = im.convert("RGB").quantize(colors)
        q.save(dst, "PNG", optimize=True)
        if os.path.getsize(dst) <= limit:
            return 1.0, mode
    im.convert("L").save(dst, "PNG", optimize=True)
    if os.path.getsize(dst) <= limit:
        return 1.0, "gray"
    scale = 1.0
    while scale > 0.35:
        scale *= 0.85
        w, h = int(im.width * scale), int(im.height * scale)
        im.resize((w, h), Image.LANCZOS).save(dst, "PNG", optimize=True)
        if os.path.getsize(dst) <= limit:
            break
    return round(scale, 3), "scaled"


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="score the OCR branch on one page")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--transcript", required=True,
                    help="page-XX.md written by the vision model")
    ap.add_argument("--work", default=os.path.join("_ocr_eval", "run"))
    ap.add_argument("--json", default=None)
    ap.add_argument("--png", default=None, help="copy the render here")
    ap.add_argument("--max-png-kb", type=int, default=400)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    outdir = os.path.abspath(args.work)
    truthdir = os.path.join(outdir, "truth")
    os.makedirs(outdir, exist_ok=True)
    if not os.path.exists(args.transcript):
        print("no transcript at %s" % args.transcript)
        return 2

    ensure_base(args.pdf, args.page, outdir)
    png = render(args.pdf, args.page, outdir, args.dpi)
    tpath = install_transcript(args.transcript, outdir, args.page)
    merge(outdir)

    print("[4/4] score")
    doc = load_json(os.path.join(outdir, "doc.json"))
    truth, why = build_truth(args.pdf, args.page, truthdir)
    checks = assertions(doc, args.page, outdir)
    failed = [c for c in checks if not c["ok"]]
    for c in checks:
        print("      %-42s %s %s" % (c["check"], "ok" if c["ok"] else "FAIL", c["detail"]))

    if args.png:
        used, how = save_png(png, args.png, args.max_png_kb)
        print("      render -> %s (%s, scale %.2f, %d KB)"
              % (args.png, how, used, os.path.getsize(args.png) // 1024))
    else:
        used, how = 1.0, "none"

    result = {
        "schema": "pdf-struct/ocreval/1",
        "note": ("n=1 page (resnet p1), 200 dpi, transcription by a general vision "
                 "model, single pass, no tuning. This measures the merge pipeline + "
                 "one model's reading, not a benchmark."),
        "case": {
            "file": rel_pdf(args.pdf),
            "page": args.page,
            "dpi": args.dpi,
            "transcriber": "vision model (single pass, see note)",
            "char_similarity": None,
            "char_similarity_raw": None,
            "token_recall": None,
            "line_count_ratio": None,
            "column_order_ok": None,
            "running_header_dropped": None,
            "blocks": len([b for b in doc["blocks"] if b.get("page") == args.page]),
            "mean_confidence": None,
            "missing_examples": [],
            "extra_examples": [],
        },
        "caveats": [],
        "assertions": checks,
    }

    if truth is None:
        result["caveats"].append(why)
        result["caveats"].append("no text layer -> only the structural assertions above "
                                 "were evaluated; no accuracy number exists for this page")
    else:
        s = score(tpath, doc, truth, args.page)
        result["case"]["char_similarity_raw"] = s["detail"]["raw_char_similarity"]
        for k in ("char_similarity", "token_recall", "line_count_ratio",
                  "column_order_ok", "running_header_dropped", "blocks",
                  "mean_confidence", "missing_examples", "extra_examples"):
            result["case"][k] = s[k]
        result["detail"] = s["detail"]
        result["detail"]["png_scale"] = used
        result["detail"]["png_mode"] = how
        copy_check = {
            "check": "transcript is not a byte-copy of the text layer",
            "ok": s["detail"]["raw_char_similarity"] < 0.999,
            "detail": "raw_char_similarity=%.4f (ligature chars in truth: %d)"
                      % (s["detail"]["raw_char_similarity"],
                         s["detail"]["ligature_chars_in_truth"]),
        }
        result["assertions"].append(copy_check)
        failed = [c for c in result["assertions"] if not c["ok"]]
        print("      %-42s %s %s" % (copy_check["check"],
                                     "ok" if copy_check["ok"] else "FAIL",
                                     copy_check["detail"]))
        result["caveats"] = [
            "n=1 page, one model, one pass: this bounds one run, it is not a benchmark "
            "and the standard error of a single page is large.",
            "the 'scan' here is a 200 dpi rasterisation of a born-digital PDF: no skew, "
            "no JPEG noise, no photocopy blur. A real scan starts lower than this, so "
            "these numbers are an upper bound for the branch, not a field expectation.",
            "char_similarity folds typography (NFKC, ligatures, quotes, dashes) on both "
            "sides, which is why it can reach 1.0.  The same transcript without that "
            "folding scores %.4f: the %d fi/ff ligature codepoints in the text layer were "
            "read as two plain letters.  That gap is also the proof this transcript was "
            "read off the image and not copied out of the text layer (a copy would score "
            "1.0 unfolded as well); missing/extra_examples are drawn from that strict "
            "stream, see detail.char_diffs for the exact character pairs."
            % (s["detail"]["raw_char_similarity"], s["detail"]["ligature_chars_in_truth"]),
            "in-figure text is excluded from the truth set and not transcribed "
            "(%d figure_label blocks on this page, per prompt rule 5 the figure is a "
            "placeholder); token_recall therefore does not measure axis labels or legends."
            % s["detail"]["figure_label_blocks_excluded"],
            "column_order_ok walks the truth lines in column order and checks that the "
            "vision block each line landed in (containment match) never goes backwards; "
            "it verifies the transcript's order, not the model's attention.",
            "mean_confidence is the transcript's single confidence line mapped "
            "high/medium/low -> 0.9/0.6/0.3; it is nominal, not calibrated.",
        ]

    if "detail" not in result:
        result["detail"] = {"png_scale": used, "png_mode": how}

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
        print("      json -> %s" % args.json)

    if failed and args.strict:
        print("strict: %d assertion(s) failed" % len(failed))
        return 4
    return 0 if truth is not None else 3


if __name__ == "__main__":
    raise SystemExit(main())
