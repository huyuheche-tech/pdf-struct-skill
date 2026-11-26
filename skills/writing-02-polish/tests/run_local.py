#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local self-test for the academic-polish skill. Not the official platform cases."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(ROOT, "scripts", "run_case.py")
CASES = os.path.join(HERE, "cases")


def run_case(case_dir, draft, extra=None):
    tmp = tempfile.mkdtemp(prefix="pl-")
    out = os.path.join(tmp, "out")
    work = os.path.join(tmp, "work")
    cmd = [sys.executable, RUN, "--case", os.path.join(case_dir, "case.json"),
           "--input-dir", case_dir, "--out", out, "--work", work]
    if draft:
        cmd += ["--draft", draft]
    cmd += list(extra or [])
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    rp = os.path.join(out, "result.json")
    res = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None
    return p, res, out


def err_codes(res):
    if not res:
        return []
    return [e["code"] for e in res["main_result"]["checks"]["errors"]]


def warn_codes(res):
    if not res:
        return []
    return [w["code"] for w in res["main_result"]["checks"]["warnings"]]


def mutated(src_draft, fn):
    payload = json.load(open(src_draft, encoding="utf-8"))
    fn(payload)
    path = os.path.join(tempfile.mkdtemp(prefix="pl-bad-"), "draft.json")
    json.dump(payload, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return path


def main():
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    # ---------------- case 01: correct polish ----------------
    d1 = os.path.join(CASES, "case-01")
    p, r, out = run_case(d1, os.path.join(d1, "draft.json"))
    add("case01.exit", p.returncode == 0, p.stdout.strip()[-200:])
    add("case01.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case01.no_errors", err_codes(r) == [], ",".join(err_codes(r)))
    m1 = (r or {}).get("main_result", {}).get("metrics", {})
    add("case01.four_edits", m1.get("edit_count") == 4, str(m1.get("edit_count")))
    add("case01.zero_drift", m1.get("number_drift") == 0 and m1.get("hedge_drift") == 0
        and m1.get("residual_grammar") == 0 and m1.get("unexplained") == 0,
        json.dumps(m1, ensure_ascii=False))
    add("case01.contract_filled",
        r and all(v is not None for v in r["output_contract"].values()),
        json.dumps(r["output_contract"], ensure_ascii=False)[:160] if r else "")
    add("case01.numbers_kept",
        r and "18.4%" in r["main_result"]["edited_text"]
        and "[3]" in r["main_result"]["edited_text"],
        "")
    add("case01.polished_md_written", os.path.exists(os.path.join(out, "polished.md")), "")
    add("case01.edits_json_written", os.path.exists(os.path.join(out, "edits.json")), "")

    # plan-only must not require a draft and must not claim success
    p2, r2, out2 = run_case(d1, None, ["--plan-only"])
    add("case01.plan_only_writes_plan", os.path.exists(os.path.join(out2, "plan.json")), "")
    add("case01.plan_only_not_success", r2 and r2["status"] != "success",
        r2["status"] if r2 else "no result")
    add("case01.plan_only_next_step",
        r2 and bool(r2["uncertainty"].get("next_step")), "")

    # ---------------- case 02: bad polish ----------------
    d2 = os.path.join(CASES, "case-02")
    p, r, _ = run_case(d2, os.path.join(d2, "draft.json"))
    c2 = err_codes(r)
    add("case02.partial", r and r["status"] == "partial", r["status"] if r else "no result")
    for code in ("hedge_strengthened", "number_missing", "citation_changed"):
        add("case02.detects_" + code, code in c2, ",".join(c2))
    m2 = (r or {}).get("main_result", {}).get("metrics", {})
    add("case02.number_drift_counted", (m2.get("number_drift") or 0) >= 1
        and (m2.get("hedge_drift") or 0) == 1, json.dumps(m2, ensure_ascii=False))

    # ---------------- case 03: Chinese ----------------
    d3 = os.path.join(CASES, "case-03")
    p, r, _ = run_case(d3, os.path.join(d3, "draft.json"))
    add("case03.exit", p.returncode == 0, p.stdout.strip()[-200:])
    add("case03.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case03.no_errors", err_codes(r) == [], ",".join(err_codes(r)))
    add("case03.term_lock_kept",
        r and any(e["type"] == "term" for e in r["main_result"]["edits"])
        and "term_missing" not in err_codes(r), "")
    add("case03.negation_kept", r and "并不显著" in r["main_result"]["edited_text"], "")

    # ---------------- negative 1: a ledger row without a reason ----------------
    bad = mutated(os.path.join(d1, "draft.json"),
                  lambda pl: pl["edits"][1].pop("reason", None))
    p, r, _ = run_case(d1, bad)
    add("negative.edit_unexplained", r and "edit_unexplained" in err_codes(r),
        ",".join(err_codes(r)))
    add("negative.edit_unexplained_is_partial", r and r["status"] == "partial",
        r["status"] if r else "no result")

    # ---------------- negative 2: negation flipped ----------------
    def flip(payload):
        payload["edited"] = payload["edited"].replace("并不显著", "显著")
        payload["edits"].append({"id": "s99", "original": "并不显著", "edited": "显著",
                                 "type": "clarity", "reason": "去掉冗余否定"})
    bad2 = mutated(os.path.join(d3, "draft.json"), flip)
    p, r, _ = run_case(d3, bad2)
    add("negative.negation_changed", r and "negation_changed" in err_codes(r),
        ",".join(err_codes(r)))

    # ---------------- negative 3: ledger row that is not in the manuscript ----------------
    def unanchor(payload):
        payload["edits"][0]["original"] = "a sentence that does not exist"
    bad3 = mutated(os.path.join(d1, "draft.json"), unanchor)
    p, r, _ = run_case(d1, bad3)
    add("negative.edit_unanchored", r and "edit_unanchored" in err_codes(r),
        ",".join(err_codes(r)))

    # ---------------- negative 4: only edited_text, no ledger ----------------
    def bare(payload):
        payload.pop("edits", None)
    bad4 = mutated(os.path.join(d1, "draft.json"), bare)
    p, r, _ = run_case(d1, bad4)
    add("negative.auto_ledger_unexplained", r and "edit_unexplained" in err_codes(r),
        ",".join(err_codes(r)))

    # ---------------- negative 5: the rewrite leaves an a/an error behind ----------
    def keep_bad_article(payload):
        payload["edited"] = payload["edited"].replace("is an important signal",
                                                      "is a important signal")
        for e in payload["edits"]:
            if e["id"] == "s03":
                e["edited"] = "is a important signal"
    bad5 = mutated(os.path.join(d1, "draft.json"), keep_bad_article)
    p, r, _ = run_case(d1, bad5)
    rg = [e for e in (r or {}).get("main_result", {}).get("checks", {}).get("errors", [])
          if e["code"] == "residual_grammar"]
    add("negative.residual_grammar", bool(rg), ",".join(err_codes(r)))
    add("negative.residual_grammar_rule", bool(rg) and rg[0].get("rule") == "a_an",
        json.dumps(rg[:1], ensure_ascii=False)[:120])

    # ---------------- no material at all ----------------
    empty = tempfile.mkdtemp(prefix="pl-empty-")
    p, r, _ = run_case(empty, None)
    add("negative.no_material_failed", r and r["status"] == "failed",
        r["status"] if r else "no result")

    failed = [c for c in checks if not c["ok"]]
    out_dir = os.path.join(ROOT, "results")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    json.dump({"checks": checks, "failed": len(failed),
               "note": "local self-test only; not the official platform cases"},
              open(os.path.join(out_dir, "local-eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for c in checks:
        line = ("PASS " if c["ok"] else "FAIL ") + c["name"]
        if not c["ok"]:
            line += " | " + c["detail"]
        print(line.encode("ascii", "replace").decode("ascii"))
    print("%d checks, %d failed" % (len(checks), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
