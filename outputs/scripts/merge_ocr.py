#!/usr/bin/env python3
"""Merge vision transcripts (`ocr/page-XX.txt`) back into `doc.json`.

Rule of the road: a vision block has no vector bbox, so it is emitted with
`bbox: null`, `bbox_source: "vision"`, and its confidence copied from the
transcript's `confidence:` line.  Nothing is invented: pages without a
transcript keep their `empty`/`unreadable` flag.

Usage:
    python scripts/merge_ocr.py out/paper [--pages all|1-6] [--require all]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re

CONF_RE = re.compile(r"^\s*confidence:\s*(high|medium|low)", re.I | re.M)


def parse_pages(spec, available):
    if not spec or spec == "all":
        return sorted(available)
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return [p for p in out if p in available]


def page_blocks(pno, text, conf):
    """Split a transcript into blocks: one block per paragraph-ish run."""
    lines = [ln.rstrip() for ln in text.lstrip("\ufeff").splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].lower().startswith("## page"):
        lines = lines[1:]
    lines = [ln for ln in lines if not CONF_RE.match(ln)]
    blocks, cur, kind = [], [], "body"
    for ln in lines:
        s = ln.strip()
        if not s:
            if cur:
                blocks.append((kind, "\n".join(cur)))
                cur = []
            kind = "body"          # [header]/[footer] runs end at a blank line
            continue
        if s.startswith("[header]") or s.startswith("[footer]"):
            if cur:
                blocks.append((kind, "\n".join(cur)))
                cur = []
            kind = "margin_artifact"
            rest = s.replace("[header]", "").replace("[footer]", "").strip()
            if rest:
                cur = [rest]
            continue
        if s.startswith("[[figure]]"):
            if cur:
                blocks.append((kind, "\n".join(cur)))
                cur = []
            blocks.append(("figure", ""))
            kind = "caption"
            continue
        if s.startswith("[[formula]]"):
            if cur:
                blocks.append((kind, "\n".join(cur)))
                cur = []
            blocks.append(("formula", s.replace("[[formula]]", "").strip()))
            kind = "body"
            continue
        if s.startswith("|") and s.endswith("|"):
            cur.append(s)
            continue
        if re.match(r"^(#{1,6})\s+\S", s):
            if cur:
                blocks.append((kind, "\n".join(cur)))
                cur = []
            blocks.append(("heading", re.sub(r"^#+\s*", "", s)))
            kind = "body"
            continue
        if kind == "margin_artifact" and re.match(r"^\s*(abstract|summary|摘要|keywords?|关键词)\s*$",
                                                 s, re.I):
            blocks.append((kind, "\n".join(cur)))
            cur, kind = [], "body"
        if kind == "margin_artifact" and len(cur) >= 3:
            # a header/footer run is a couple of lines; more means the
            # transcript lost its blank-line separation
            blocks.append((kind, "\n".join(cur)))
            cur, kind = [], "body"
        cur.append(ln)
    if cur:
        blocks.append((kind, "\n".join(cur)))
    out = []
    for i, (kind, body) in enumerate(blocks):
        out.append({"id": "p%d-v%03d" % (pno, i), "page": pno, "order": i,
                    "page_order": i, "column": -1, "type": kind,
                    "text": body.strip(), "raw": body.strip(),
                    "bbox": None, "bbox_source": "vision",
                    "source": "vision", "confidence": conf,
                    "n_lines": len(body.splitlines()),
                    "size": None, "bold": False, "italic": False,
                    "mono": False, "font": "", "sup_sub": None})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="merge vision transcripts into doc.json")
    ap.add_argument("outdir")
    ap.add_argument("--pages", default="all")
    ap.add_argument("--require", default="any", choices=["any", "all"],
                    help="fail if some requested page has no transcript")
    args = ap.parse_args(argv)

    doc_path = os.path.join(args.outdir, "doc.json")
    with open(doc_path, encoding="utf-8") as fh:
        doc = json.load(fh)

    avail = {}
    for p in glob.glob(os.path.join(args.outdir, "ocr", "page-*.txt")):
        m = re.search(r"page-(\d+)\.txt$", p)
        if m:
            avail[int(m.group(1))] = p
    if not avail:
        print("no transcripts found under %s/ocr/" % args.outdir)
        return 2
    todo = parse_pages(args.pages, set(avail))
    missing = [p for p in todo if p not in avail]
    if missing and args.require == "all":
        print("missing transcripts for pages: %s" % missing)
        return 2

    added, pages_done = 0, []
    for pno in todo:
        with open(avail[pno], encoding="utf-8") as fh:
            text = fh.read()
        m = CONF_RE.search(text)
        conf = (m.group(1).lower() if m else "unknown")
        blocks = page_blocks(pno, text, conf)
        doc["blocks"] = [b for b in doc["blocks"] if b.get("page") != pno] + blocks
        for pg in doc["pages"]:
            if pg.get("page") == pno:
                pg["ocr"] = True
                pg["ocr_confidence"] = conf
                pg["empty"] = False
                pg["text_layer_chars"] = pg.get("text_layer_chars") or 0
        added += len(blocks)
        pages_done.append(pno)

    doc["blocks"].sort(key=lambda b: (b.get("page") or 0,
                                      b.get("page_order") if b.get("page_order") is not None else 0))
    types = {}
    for b in doc["blocks"]:
        types[b["type"]] = types.get(b["type"], 0) + 1
    doc["stats"]["types"] = dict(sorted(types.items()))
    doc["stats"]["n_blocks"] = len(doc["blocks"])
    doc["stats"]["ocr_pages"] = pages_done
    doc["stats"]["ocr_blocks"] = added
    doc["stats"]["note"] = ("blocks from vision have bbox=null and bbox_source=vision; "
                            "they are traceable to a page, not to a vector box")
    with open(doc_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)

    md = os.path.join(args.outdir, "ocr", "text.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write("# vision transcription of %s\n\n" % doc["source"]["path"])
        for pno in sorted(pages_done):
            with open(avail[pno], encoding="utf-8") as f2:
                fh.write("\n<!-- ===== page %d (vision, no vector bbox) -->\n" % pno)
                fh.write(f2.read().rstrip() + "\n")
    print("merged %d page(s), %d blocks -> %s" % (len(pages_done), added, doc_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())