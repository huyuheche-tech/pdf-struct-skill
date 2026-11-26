#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local self-test for the LaTeX build doctor. Not the official platform cases.

Run:  python tests/run_local.py
Exit code is 1 when any check fails.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(ROOT, "scripts", "run_case.py")
CASES = os.path.join(HERE, "cases")
PY = sys.executable


def run_case(case_dir, draft=None, do_fix=False, no_compile=True):
    tmp = tempfile.mkdtemp(prefix="tx-")
    out = os.path.join(tmp, "out")
    work = os.path.join(tmp, "work")
    cmd = [PY, RUN, "--case", os.path.join(case_dir, "case.json"),
           "--input-dir", case_dir, "--out", out, "--work", work]
    if draft:
        cmd += ["--draft", draft]
    if do_fix:
        cmd += ["--fix"]
    if no_compile:
        cmd += ["--no-compile"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    rp = os.path.join(out, "result.json")
    res = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None
    fixed = os.path.join(out, "fixed.tex")
    fixed_text = open(fixed, encoding="utf-8").read() if os.path.exists(fixed) else ""
    report = os.path.join(out, "report.md")
    report_text = open(report, encoding="utf-8").read() if os.path.exists(report) else ""
    return p, res, fixed_text, report_text


def codes(res, key="errors"):
    if not res:
        return []
    return [e["code"] for e in res["main_result"]["checks"][key]]


def main():
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    d1 = os.path.join(CASES, "case-01")
    p, r, _fx, rep = run_case(d1)
    add("case01.exit", p.returncode == 0, p.stdout.strip()[-300:])
    add("case01.partial", r and r["status"] == "partial", r["status"] if r else "no result")
    e1 = codes(r)
    for code in ("cite_undefined", "label_duplicate", "table_column_mismatch",
                 "unbalanced_math"):
        add("case01.detects_" + code, code in e1, ",".join(e1))
    add("case01.warns_caption_missing", "caption_missing" in codes(r, "warnings"),
        ",".join(codes(r, "warnings")))
    add("case01.contract_filled",
        r and bool(r["output_contract"]) and all(v is not None for v in r["output_contract"].values()),
        json.dumps(r["output_contract"], ensure_ascii=False)[:200] if r else "")
    anchored = bool(r) and all(e.get("file") and e.get("line", 0) >= 1 and e.get("text")
                               for e in r["main_result"]["checks"]["errors"])
    add("case01.errors_have_file_line_and_source", anchored,
        json.dumps((r or {}).get("main_result", {}).get("checks", {}).get("errors", [])[:1],
                   ensure_ascii=False)[:200])

    d2 = os.path.join(CASES, "case-02")
    p, r2, _fx2, rep2 = run_case(d2, draft=os.path.join(d2, "draft.tex"))
    add("case02.success", r2 and r2["status"] == "success", r2["status"] if r2 else "no result")
    add("case02.no_errors", codes(r2) == [], ",".join(codes(r2)))
    m2 = (r2 or {}).get("main_result", {}).get("metrics", {})
    add("case02.compiled_false", m2.get("compiled") is False, str(m2.get("compiled")))
    add("case02.no_fake_compile_claim", "编译通过" not in rep2, "report.md claims a compile")
    add("case02.no_compile_error_when_missing",
        "compile_error" not in codes(r2), ",".join(codes(r2)))

    d3 = os.path.join(CASES, "case-03")
    p, r3, _fx3, _rep3 = run_case(d3, draft=os.path.join(d3, "draft.tex"))
    add("case03.success", r3 and r3["status"] == "success", r3["status"] if r3 else "no result")
    add("case03.no_errors", codes(r3) == [], ",".join(codes(r3)))
    m3 = (r3 or {}).get("main_result", {}).get("metrics", {})
    add("case03.three_citations", m3.get("cite_keys", 0) >= 3, str(m3.get("cite_keys")))
    add("case03.two_equations", m3.get("labels", 0) >= 2, str(m3.get("labels")))

    # negative 1: --fix must remove the duplicate label and keep \ref in sync
    p, r, fixed, _rep = run_case(d1, do_fix=True)
    add("negative.fix_removes_duplicate_label",
        fixed.count("\\label{sec:res}") == 1 and "\\label{sec:res-2}" in fixed,
        "occurrences=%d" % fixed.count("\\label{sec:res}"))
    add("negative.fix_syncs_ref", "\\ref{sec:res-2}" in fixed, "")
    add("negative.fix_marks_todo_cite",
        "TODO-unknown2021" in fixed and "cite_undefined" not in codes(r), ",".join(codes(r)))
    # negative 2: --fix must NOT silently repair the table (only a patch plan)
    add("negative.fix_leaves_table_for_human",
        "table_column_mismatch" in codes(r) and "71.8 & extra" in fixed, ",".join(codes(r)))
    # negative 3: with no compiler, compiled must stay false and must be disclosed
    add("negative.compiled_stays_false",
        r and r["main_result"]["metrics"]["compiled"] is False
        and r["main_result"]["diagnostics"]["compile"].get("compiler_missing") is True,
        json.dumps((r or {}).get("main_result", {}).get("metrics"), ensure_ascii=False))

    failed = [c for c in checks if not c["ok"]]
    out_dir = os.path.join(ROOT, "results")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    json.dump({"checks": checks, "failed": len(failed),
               "note": "local self-test only; not the official platform cases"},
              open(os.path.join(out_dir, "local-eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"]
              + (" | " + c["detail"] if not c["ok"] else ""))
    print("%d checks, %d failed" % (len(checks), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
