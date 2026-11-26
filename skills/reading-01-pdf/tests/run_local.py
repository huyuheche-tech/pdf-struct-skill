#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local runtime test for the pdf-struct skill (3 synthetic fixtures).

This complements tests/test_engine.py (27 assertions) and
tests/test_robustness.py (55 assertions): it exercises the *platform entry*
scripts/run_case.py, i.e. case.json -> result.json + output_contract.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(ROOT, "scripts", "run_case.py")
FIX = os.path.join(HERE, "fixtures")
CASES = os.path.join(HERE, "cases")


def run(case_name, case_path=None, extra=None):
    tmp = tempfile.mkdtemp(prefix="pdf-")
    out = os.path.join(tmp, "out")
    work = os.path.join(tmp, "work")
    cmd = [sys.executable, RUN, "--case", case_path or os.path.join(CASES, case_name, "case.json"),
           "--input-dir", FIX, "--out", out, "--work", work]
    if extra:
        cmd += extra
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    rp = os.path.join(out, "result.json")
    res = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None
    return p, res


def main():
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    p, r = run("case-01")
    add("case01.exit", p.returncode == 0, p.stdout.strip()[-160:])
    add("case01.status", r and r["status"] == "success", r["status"] if r else "none")
    add("case01.pages", r and r["main_result"]["documents"][0]["pages"] == 1,
        str(r["main_result"]["documents"][0]["pages"]) if r else "")
    add("case01.sections", r and len(r["main_result"]["documents"][0]["sections"]) >= 5,
        str(len(r["main_result"]["documents"][0]["sections"])) if r else "")
    add("case01.tables", r and len(r["main_result"]["documents"][0]["tables"]) >= 1,
        str(len(r["main_result"]["documents"][0]["tables"])) if r else "")
    add("case01.contract_filled",
        r and all(k in r["output_contract"] for k in
                  ("title", "sections", "tables", "pages", "text", "status")),
        json.dumps(r.get("output_contract", {}), ensure_ascii=False)[:120] if r else "")
    add("case01.recall", r and (r["main_result"]["documents"][0]["char_recall"] or 0) > 0.9,
        str(r["main_result"]["documents"][0]["char_recall"]) if r else "")

    p, r = run("case-02")
    add("case02.status", r and r["status"] == "success", r["status"] if r else "none")
    secs = (r or {}).get("main_result", {}).get("documents", [{}])[0].get("sections", [])
    add("case02.two_sections", len(secs) >= 2, str(len(secs)))
    add("case02.has_level2", any(s.get("level") == 2 for s in secs), str(secs)[:160])
    add("case02.title_alias", r and r["output_contract"].get("document_title") is not None,
        str((r or {}).get("output_contract", {}).get("document_title"))[:80])

    p, r = run("case-03")
    add("case03.partial", r and r["status"] == "partial", r["status"] if r else "none")
    ws = (r or {}).get("uncertainty", {}).get("warnings", [])
    add("case03.no_text_layer", any(w.get("code") == "no_text_layer" for w in ws),
        json.dumps(ws, ensure_ascii=False)[:200])
    add("case03.no_fabricated_text", r and r["output_contract"].get("text") is None,
        str((r or {}).get("output_contract", {}).get("text"))[:60])

    # negative: a text file renamed .pdf must fail honestly, not crash
    tmp = tempfile.mkdtemp(prefix="pdf-bad-")
    bad = os.path.join(tmp, "broken.pdf")
    open(bad, "w", encoding="utf-8").write("not a pdf")
    cp = os.path.join(tmp, "case.json")
    json.dump({"case_id": "broken", "input": "broken.pdf",
               "output_contract": ["pages", "text"]}, open(cp, "w", encoding="utf-8"))
    p, r = run(None, case_path=cp)
    add("negative.broken_pdf_status", r and r["status"] == "failed", r["status"] if r else "none")
    add("negative.broken_pdf_warning",
        r and any(w.get("code") == "parse_failed" for w in r["uncertainty"]["warnings"]),
        json.dumps((r or {}).get("uncertainty", {}), ensure_ascii=False)[:200])

    # negative: an unknown contract field is reported, not silently invented
    cp2 = os.path.join(tmp, "case2.json")
    json.dump({"case_id": "unknown-field", "input": "cjk-2col.pdf",
               "output_contract": ["sections", "layout_semantics_v9"]},
              open(cp2, "w", encoding="utf-8"))
    p, r = run(None, case_path=cp2)
    add("negative.unknown_field_reported",
        r and "layout_semantics_v9" in r.get("contract_unresolved", []),
        json.dumps((r or {}).get("contract_unresolved")))

    failed = [c for c in checks if not c["ok"]]
    out_dir = os.path.join(ROOT, "results")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    json.dump({"checks": checks, "failed": len(failed),
               "note": "local runtime test on synthetic fixtures; not the official cases"},
              open(os.path.join(out_dir, "local-eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] +
              ("" if c["ok"] else " | " + c["detail"]))
    print("%d checks, %d failed" % (len(checks), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
