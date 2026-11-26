#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local self-test for the translation skill. Not the official platform cases."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(ROOT, "scripts", "run_case.py")
CASES = os.path.join(HERE, "cases")


def run_case(case_dir, draft):
    tmp = tempfile.mkdtemp(prefix="tr-")
    out = os.path.join(tmp, "out")
    work = os.path.join(tmp, "work")
    cmd = [sys.executable, RUN, "--case", os.path.join(case_dir, "case.json"),
           "--input-dir", case_dir, "--out", out, "--work", work]
    if draft:
        cmd += ["--draft", draft]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    rp = os.path.join(out, "result.json")
    res = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None
    return p, res


def codes(res):
    if not res:
        return []
    return [e["code"] for e in res["main_result"]["checks"]["errors"]]


def main():
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    d1 = os.path.join(CASES, "case-01")
    p, r = run_case(d1, os.path.join(d1, "draft.json"))
    add("case01.exit", p.returncode == 0, p.stdout.strip()[-200:])
    add("case01.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case01.no_errors", codes(r) == [], ",".join(codes(r)))
    add("case01.covers_3_segments", r and len(r["main_result"]["segments"]) == 3,
        str(len(r["main_result"]["segments"])) if r else "0")
    add("case01.contract_filled",
        r and all(v is not None for v in r["output_contract"].values()),
        json.dumps(r["output_contract"], ensure_ascii=False)[:200] if r else "")
    gm = (r or {}).get("main_result", {}).get("glossary", [])
    add("case01.glossary_consistent", bool(gm) and all(g["consistent"] for g in gm),
        json.dumps(gm, ensure_ascii=False)[:200])

    d2 = os.path.join(CASES, "case-02")
    p, r = run_case(d2, os.path.join(d2, "draft.json"))
    c2 = codes(r)
    add("case02.partial", r and r["status"] == "partial", r["status"] if r else "no result")
    for code in ("negation_lost", "number_missing", "formula_changed"):
        add("case02.detects_" + code, code in c2, ",".join(c2))

    d3 = os.path.join(CASES, "case-03")
    p, r = run_case(d3, os.path.join(d3, "draft.json"))
    add("case03.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case03.no_errors", codes(r) == [], ",".join(codes(r)))
    gm = (r or {}).get("main_result", {}).get("glossary", [])
    add("case03.glossary_enforced", bool(gm) and all(g["consistent"] for g in gm),
        json.dumps(gm, ensure_ascii=False)[:200])

    # negative: dropping a paragraph must be caught, not silently accepted
    bad = os.path.join(tempfile.mkdtemp(prefix="tr-bad-"), "draft.json")
    payload = json.load(open(os.path.join(d1, "draft.json"), encoding="utf-8"))
    payload["segments"] = [s for s in payload["segments"] if s["id"] != "p003"]
    json.dump(payload, open(bad, "w", encoding="utf-8"), ensure_ascii=False)
    p, r = run_case(d1, bad)
    add("negative.missing_segment", r and "missing_segment" in codes(r), ",".join(codes(r)))

    # negative: a changed term must be caught
    bad2 = os.path.join(tempfile.mkdtemp(prefix="tr-bad2-"), "draft.json")
    payload = json.load(open(os.path.join(d1, "draft.json"), encoding="utf-8"))
    for s in payload["segments"]:
        s["target"] = s["target"].replace("注意力机制", "关注力机制")
    json.dump(payload, open(bad2, "w", encoding="utf-8"), ensure_ascii=False)
    p, r = run_case(d1, bad2)
    add("negative.term_missing", r and "term_missing" in codes(r), ",".join(codes(r)))

    failed = [c for c in checks if not c["ok"]]
    out_dir = os.path.join(ROOT, "results")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    json.dump({"checks": checks, "failed": len(failed),
               "note": "local self-test only; not the official platform cases"},
              open(os.path.join(out_dir, "local-eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + (" | " + c["detail"] if not c["ok"] else ""))
    print("%d checks, %d failed" % (len(checks), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
