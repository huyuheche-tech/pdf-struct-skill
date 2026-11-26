#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local self-test for the introduction skill. Not the official platform cases."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(ROOT, "scripts", "run_case.py")
CASES = os.path.join(HERE, "cases")
SECTIONS = ("background", "related_work", "gap", "contributions")


def run_case(case_dir, draft):
    tmp = tempfile.mkdtemp(prefix="intro-")
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


def patch(draft_path, out_path, mutate):
    payload = json.load(open(draft_path, encoding="utf-8"))
    mutate(payload)
    json.dump(payload, open(out_path, "w", encoding="utf-8"), ensure_ascii=False)


def main():
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    d1 = os.path.join(CASES, "case-01")
    p, r = run_case(d1, os.path.join(d1, "draft.json"))
    add("case01.exit", p.returncode == 0, p.stdout.strip()[-200:])
    add("case01.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case01.no_errors", codes(r) == [], ",".join(codes(r)))
    secs = (r or {}).get("main_result", {}).get("sections", {})
    add("case01.four_sections", all(secs.get(k) for k in SECTIONS),
        json.dumps({k: bool(secs.get(k)) for k in SECTIONS}))
    met = (r or {}).get("main_result", {}).get("metrics", {})
    add("case01.contributions_bound", met.get("bound") == met.get("contributions") == 3,
        json.dumps(met))
    add("case01.contract_filled",
        r and all(v is not None for v in r["output_contract"].values()),
        json.dumps((r or {}).get("output_contract", {}), ensure_ascii=False)[:200])

    d2 = os.path.join(CASES, "case-02")
    p, r = run_case(d2, os.path.join(d2, "draft.json"))
    c2 = codes(r)
    add("case02.partial", r and r["status"] == "partial", r["status"] if r else "no result")
    for code in ("claim_unsupported", "contribution_unbound", "gap_unsupported"):
        add("case02.detects_" + code, code in c2, ",".join(c2))

    d3 = os.path.join(CASES, "case-03")
    p, r = run_case(d3, os.path.join(d3, "draft.json"))
    add("case03.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case03.no_errors", codes(r) == [], ",".join(codes(r)))
    met3 = (r or {}).get("main_result", {}).get("metrics", {})
    add("case03.groups_two", met3.get("groups") == 2, json.dumps(met3))

    # negative: deleting the background section must be caught
    bad = os.path.join(tempfile.mkdtemp(prefix="intro-bad-"), "draft.json")
    patch(os.path.join(d1, "draft.json"), bad,
          lambda d: d["sections"].pop("background", None))
    p, r = run_case(d1, bad)
    add("negative.section_missing", r and "section_missing" in codes(r),
        ",".join(codes(r)))

    # negative: citing a key that is not in the bibliography must be caught
    bad2 = os.path.join(tempfile.mkdtemp(prefix="intro-bad2-"), "draft.json")
    patch(os.path.join(d1, "draft.json"), bad2,
          lambda d: d["sections"].update(
              {"background": d["sections"]["background"].replace("liu2019", "nokey2099")}))
    p, r = run_case(d1, bad2)
    add("negative.citation_unknown", r and "citation_unknown" in codes(r),
        ",".join(codes(r)))

    failed = [c for c in checks if not c["ok"]]
    out_dir = os.path.join(ROOT, "results")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    json.dump({"checks": checks, "failed": len(failed),
               "note": "local self-test only; not the official platform cases"},
              open(os.path.join(out_dir, "local-eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] +
              (" | " + c["detail"] if not c["ok"] else ""))
    print("%d checks, %d failed" % (len(checks), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
