#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local self-test for the methods skill. Not the official platform cases."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(ROOT, "scripts", "run_case.py")
CASES = os.path.join(HERE, "cases")


def run_case(case_dir, draft):
    tmp = tempfile.mkdtemp(prefix="methods-")
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
    tables = (r or {}).get("main_result", {}).get("tables", [])
    add("case01.params_ge_8", len(tables) >= 8, str(len(tables)))
    met = (r or {}).get("main_result", {}).get("metrics", {})
    add("case01.coverage_full", met.get("coverage") == 1.0, json.dumps(met))
    add("case01.repro_items_8", met.get("repro_items") == 8, json.dumps(met))
    add("case01.contract_filled",
        r and all(v is not None for v in r["output_contract"].values()),
        json.dumps((r or {}).get("output_contract", {}), ensure_ascii=False)[:200])

    d2 = os.path.join(CASES, "case-02")
    p, r = run_case(d2, os.path.join(d2, "draft.json"))
    c2 = codes(r)
    add("case02.partial", r and r["status"] == "partial", r["status"] if r else "no result")
    add("case02.detects_number_unsourced", "number_unsourced" in c2, ",".join(c2))
    add("case02.detects_repro_gap", "repro_gap" in c2, ",".join(c2))

    d3 = os.path.join(CASES, "case-03")
    p, r = run_case(d3, os.path.join(d3, "draft.json"))
    add("case03.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case03.no_errors", codes(r) == [], ",".join(codes(r)))
    add("case03.table_params", len((r or {}).get("main_result", {}).get("tables", [])) >= 8,
        str(len((r or {}).get("main_result", {}).get("tables", []))))

    # negative: config says batch 128 but the draft still says 64 -> unsourced
    tmp = tempfile.mkdtemp(prefix="methods-bad-")
    bad_case = os.path.join(tmp, "case")
    shutil.copytree(d1, bad_case)
    cfg = json.load(open(os.path.join(bad_case, "config.json"), encoding="utf-8"))
    cfg["training"]["batch_size"] = 128
    json.dump(cfg, open(os.path.join(bad_case, "config.json"), "w", encoding="utf-8"))
    p, r = run_case(bad_case, os.path.join(bad_case, "draft.json"))
    add("negative.batch_128_unsourced", r and "number_unsourced" in codes(r),
        ",".join(codes(r)))

    # negative: deleting the dataset version must leave the dataset underspecified
    bad = os.path.join(tempfile.mkdtemp(prefix="methods-bad2-"), "draft.json")
    payload = json.load(open(os.path.join(d1, "draft.json"), encoding="utf-8"))
    payload["methods"] = payload["methods"].replace(" (version 2.0)", "")
    json.dump(payload, open(bad, "w", encoding="utf-8"), ensure_ascii=False)
    p, r = run_case(d1, bad)
    add("negative.dataset_underspecified", r and "dataset_underspecified" in codes(r),
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
