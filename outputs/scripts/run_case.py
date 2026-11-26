#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry point for the pdf-struct skill.

The evaluator installs this skill under /skills/weekly-skill, drops the case at
/input/case.json (+ task.md and the material), and expects a machine-readable
/app/output/result.json that carries every field of the case's output_contract.

This wrapper does three things and nothing else:

  1. resolve the case file and the PDF(s) it points at (never assume a filename);
  2. run the deterministic parser (parse_pdf.py) for each PDF;
  3. write result.json + the parsed artifacts under /app/output.

It never invents content: if the PDF has no text layer, the result is marked
"partial" and the OCR branch is named as the next step instead of guessing.

Local use:
    python scripts/run_case.py --case tests/case.example.json --out /tmp/out
"""
import argparse
import glob
import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
PARSE = os.path.join(HERE, "parse_pdf.py")

DEFAULT_CONTRACT = ["title", "sections", "tables", "formulas", "references",
                    "pages", "text"]


def jload(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def jdump(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            for s in walk_strings(v):
                yield s
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            for s in walk_strings(v):
                yield s


def find_pdfs(case, case_path, input_dir):
    """Collect PDF paths from the case JSON, then from the input directory.

    Order matters: an explicit path in case.json wins; a directory scan is the
    fallback so a case that only says {"input": "/input"} still works.
    """
    base = os.path.dirname(os.path.abspath(case_path)) if case_path else input_dir
    found = []
    for s in walk_strings(case):
        if not s.lower().endswith(".pdf"):
            continue
        for cand in (s, os.path.join(base, s), os.path.join(input_dir, s)):
            if os.path.isfile(cand):
                found.append(os.path.abspath(cand))
                break
    if not found and os.path.isdir(input_dir):
        found = sorted(glob.glob(os.path.join(input_dir, "**", "*.pdf"), recursive=True))
    # de-duplicate, keep order
    seen, out = set(), []
    for p in found:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def case_id_of(case, pdfs):
    for k in ("case_id", "caseId", "id", "slug"):
        v = case.get(k) if isinstance(case, dict) else None
        if isinstance(v, str) and v.strip():
            return v.strip()
    if pdfs:
        return os.path.splitext(os.path.basename(pdfs[0]))[0]
    return "unknown-case"


def contract_of(case):
    if not isinstance(case, dict):
        return list(DEFAULT_CONTRACT)
    oc = case.get("output_contract") or case.get("outputContract")
    if isinstance(oc, dict):
        req = oc.get("fields") or oc.get("required") or list(oc.keys())
        if isinstance(req, dict):
            req = list(req.keys())
        if isinstance(req, list) and req:
            return [str(x) for x in req]
    if isinstance(oc, list) and oc:
        return [str(x) for x in oc]
    return list(DEFAULT_CONTRACT)


def parse_one(pdf, workdir):
    stem = os.path.splitext(os.path.basename(pdf))[0]
    out = os.path.join(workdir, "parse-" + stem)
    os.makedirs(out, exist_ok=True)
    cmd = [sys.executable, PARSE, pdf, "--out", out, "--no-overlay"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=840)
    doc = None
    dp = os.path.join(out, "doc.json")
    if os.path.exists(dp):
        try:
            doc = jload(dp)
        except Exception:
            doc = None
    return p, out, doc


def summarize(pdf, outdir, doc):
    stats = (doc or {}).get("stats") or {}
    meta = (doc or {}).get("metadata") or {}
    sections = (doc or {}).get("sections") or []
    tables = (doc or {}).get("tables") or []
    return {
        "file": os.path.basename(pdf),
        "pdf_path": pdf,
        "pages": (doc or {}).get("document", {}).get("pages")
                 or stats.get("n_pages_parsed"),
        "title": (meta.get("title") or {}).get("text") if isinstance(meta.get("title"), dict)
                 else meta.get("title"),
        "sections": [{"path": s.get("path"), "level": s.get("level"),
                      "page": s.get("page")} for s in sections],
        "tables": [{"id": t.get("id"), "page": t.get("page"),
                    "rows": t.get("n_rows"), "cols": t.get("n_cols")} for t in tables],
        "figures": stats.get("n_figures"),
        "formulas": stats.get("n_formulas"),
        "references": (stats.get("types") or {}).get("reference", 0),
        "char_recall": stats.get("char_recall"),
        "selfcheck_ok": (doc or {}).get("selfcheck", {}).get("ok"),
        "text_md": os.path.join(outdir, "text.md") if os.path.exists(os.path.join(outdir, "text.md")) else None,
        "doc_json": os.path.join(outdir, "doc.json") if doc else None,
        "tables_dir": os.path.join(outdir, "tables") if os.path.isdir(os.path.join(outdir, "tables")) else None,
    }


def fill_contract(fields, docs):
    """Map the case's requested field names to values we actually computed.

    Unknown names are returned as null with a note, never as a guess.
    """
    first = docs[0] if docs else {}
    values = {
        "title": first.get("title"),
        "sections": first.get("sections"),
        "tables": first.get("tables"),
        "formulas": first.get("formulas"),
        "references": first.get("references"),
        "pages": first.get("pages"),
        "text": first.get("text_md"),
        "documents": docs,
    }
    out, missing = {}, []
    for f in fields:
        key = f.strip()
        if key in values:
            out[key] = values[key]
        else:
            out[key] = None
            missing.append(key)
    return out, missing


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default=None, help="default: /input/case.json")
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    a = ap.parse_args(argv)

    case_path = a.case or os.path.join(a.input_dir, "case.json")
    case = {}
    if os.path.exists(case_path):
        try:
            case = jload(case_path)
        except Exception as exc:
            case = {"_case_read_error": "%s: %s" % (type(exc).__name__, exc)}

    input_dir = a.input_dir if os.path.isdir(a.input_dir) else os.path.dirname(case_path) or "."
    out_dir = a.out
    work_dir = a.work
    try:
        os.makedirs(work_dir, exist_ok=True)
    except OSError:
        work_dir = os.path.join(out_dir, "work")
        os.makedirs(work_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    pdfs = find_pdfs(case, case_path, input_dir)
    cid = case_id_of(case, pdfs)
    docs, runs, sources, warnings = [], [], [], []

    for pdf in pdfs:
        p, outdir, doc = parse_one(pdf, work_dir)
        runs.append({"file": os.path.basename(pdf), "exit": p.returncode,
                     "stderr": (p.stderr or "").strip()[-600:]})
        sources.append({"file": os.path.basename(pdf), "sha256": sha256(pdf),
                        "bytes": os.path.getsize(pdf)})
        if doc:
            docs.append(summarize(pdf, outdir, doc))
            # ship the human-readable artifacts next to result.json
            for name in ("text.md", "doc.json"):
                src = os.path.join(outdir, name)
                if os.path.exists(src):
                    dst = os.path.join(out_dir, "%s.%s" % (
                        os.path.splitext(os.path.basename(pdf))[0], name))
                    with open(src, "rb") as fi, open(dst, "wb") as fo:
                        fo.write(fi.read())
        elif p.returncode == 3:
            warnings.append({
                "file": os.path.basename(pdf),
                "code": "no_text_layer",
                "detail": "parse_pdf exit 3: run scripts/ocr_pages.py, transcribe "
                          "each ocr/prompt-XX.md into ocr/page-XX.md, then "
                          "scripts/merge_ocr.py --require all",
            })
        else:
            warnings.append({"file": os.path.basename(pdf), "code": "parse_failed",
                             "detail": (p.stderr or "").strip()[-300:]})

    status = "success"
    if not docs:
        status = "failed"
    elif warnings or any(not d.get("selfcheck_ok") for d in docs):
        status = "partial"

    fields = contract_of(case)
    contract, missing = fill_contract(fields, docs)

    result = {
        "schema": "weekly-skill/result/1",
        "skill": "weekly-skill",
        "case_id": cid,
        "task": "文献文档解析",
        "status": status,
        "main_result": {
            "documents": docs,
            "summary": ("%d PDF(s), %d page(s), %d section(s), %d table(s)"
                        % (len(docs), sum(int(d.get("pages") or 0) for d in docs),
                           sum(len(d.get("sections") or []) for d in docs),
                           sum(len(d.get("tables") or []) for d in docs))),
        },
        "evidence": {
            "type": "page + bbox",
            "note": ("every block in the shipped doc.json carries page and bbox; "
                     "text.md prefixes each block with <!-- p<page>-b<order> -->"),
            "anchors": [{"file": d["file"], "pages": d.get("pages"),
                         "doc_json": os.path.basename(d.get("doc_json") or "")}
                        for d in docs],
        },
        "uncertainty": {
            "warnings": warnings,
            "missing_fields": missing,
            "note": ("unreadable pages are reported, not guessed; a partial parse "
                     "is marked partial rather than completed with invented text"),
        },
        "sources": sources,
        "output_contract": contract,
        "runs": runs,
    }
    jdump(os.path.join(out_dir, "result.json"), result)

    # a human can read this without opening the JSON
    lines = ["# %s" % cid, "", "status: **%s**" % status, ""]
    for d in docs:
        lines.append("- `%s`: %s pages, %s sections, %s tables, recall=%s"
                     % (d["file"], d.get("pages"), len(d.get("sections") or []),
                        len(d.get("tables") or []), d.get("char_recall")))
    for w in warnings:
        lines.append("- WARNING `%s`: %s" % (w.get("code"), str(w.get("detail"))[:200]))
    with io.open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8",
                 newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("case_id=%s status=%s pdfs=%d docs=%d" % (cid, status, len(pdfs), len(docs)))
    print("wrote %s" % os.path.join(out_dir, "result.json"))
    return 0 if status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
