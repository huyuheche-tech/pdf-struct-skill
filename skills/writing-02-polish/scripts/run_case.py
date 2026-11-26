#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry for the academic-polish skill.

Two-phase by design, because a deterministic script must not invent a rewrite:

    # phase 1 -- sentence plan: ids, numbers, citations, locked terms
    python scripts/run_case.py --plan-only

    # phase 2 -- validate the model-authored draft and write result.json
    python scripts/run_case.py --draft /app/work/draft.json

With no --draft the script still writes result.json (status=partial) plus
plan.json, so a single run yields a usable hand-off rather than a fake polish.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skillkit as sk          # noqa: E402
import polish_ledger as pl     # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default=None)
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--draft", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--plan-only", action="store_true")
    a = ap.parse_args(argv)

    case_path = a.case or os.path.join(a.input_dir, "case.json")
    case, case_path = sk.load_case(case_path)
    input_dir = a.input_dir if os.path.isdir(a.input_dir) else (os.path.dirname(case_path) or ".")
    out_dir, work_dir = a.out, a.work
    for d in (out_dir, work_dir):
        if not os.path.isdir(d):
            os.makedirs(d)

    materials = sk.material_texts(case, case_path, input_dir)
    # --plan-only means "build the plan, validate nothing": a draft lying next to
    # the case must not be picked up, or phase 1 would silently report success.
    draft_path = None if a.plan_only else (a.draft or sk.find_draft(case, case_path, input_dir))
    r = pl.run(case, materials, out_dir, draft_path=draft_path, title=a.title)

    main_result = r["main"]
    warnings = r.get("warnings", [])
    uncertainty = {
        "warnings": warnings,
        "human_review": [w for w in warnings if w.get("code") in
                         ("hedge_weakened", "alignment_gap", "edit_noop",
                          "edit_duplicate_id", "draft_missing")],
        "missing_fields": [],
        "note": ("deterministic guard: sentence alignment, edit ledger completeness, "
                 "number/unit multiset, citation markers, hedge strength, negation "
                 "polarity, locked terminology, high-confidence grammar lint. "
                 "Whether the prose actually reads better needs human review."),
    }
    if r["status"] == "failed":
        uncertainty["next_step"] = ("no readable manuscript under the input dir; provide a "
                                    ".md/.txt/.pdf with a text layer")
    elif not draft_path:
        uncertainty["next_step"] = (
            "write /app/work/draft.json as {\"edited\": \"<full polished text>\", "
            "\"edits\": [{\"id\":\"s01\",\"original\":\"...\",\"edited\":\"...\","
            "\"type\":\"grammar|term|tone|clarity\",\"reason\":\"...\"}]} "
            "then rerun with --draft")
    elif not (main_result.get("edited_text") or "").strip():
        uncertainty["next_step"] = ("the draft carries no editable text; add \"edited\" "
                                    "(or \"edited_text\") and rerun with --draft")

    result = sk.write_result(
        out_dir, "academic-polish-ledger", "学术语言润色（句级台账）", case, r["status"],
        main_result,
        evidence={"anchors": [{"sentence": s["id"], "op": s["op"],
                               "change_type": s["change_type"]}
                              for s in main_result.get("checks", {}).get("sentences", [])],
                  "method": "difflib sentence alignment + multiset/极性 checks on the source",
                  "edited_sha256": None},
        uncertainty=uncertainty,
        sources=sk.sources_of(r.get("sources", [])),
        runs=[{"step": "polish_ledger", "status": r["status"],
               "errors": len(r.get("errors", [])), "warnings": len(warnings)}],
    )

    lines = ["- status: **%s**" % result["status"],
             "- edits: %d (unexplained %d)" % (
                 main_result.get("metrics", {}).get("edit_count", 0),
                 main_result.get("metrics", {}).get("unexplained", 0)),
             "- number_drift: %d, hedge_drift: %d, residual_grammar: %d" % (
                 main_result.get("metrics", {}).get("number_drift", 0),
                 main_result.get("metrics", {}).get("hedge_drift", 0),
                 main_result.get("metrics", {}).get("residual_grammar", 0)),
             "- errors: %d, warnings: %d" % (len(r.get("errors", [])), len(warnings))]
    for e in r.get("errors", [])[:12]:
        lines.append("- ERROR `%s` %s: %s" % (e.get("code"), e.get("id", ""), e.get("detail")))
    sk.write_report(out_dir, "polish / %s" % result["case_id"], lines)

    if a.plan_only:
        plan_path = os.path.join(out_dir, "plan.json")
        n = len(sk.jload(plan_path).get("sentences", [])) if os.path.exists(plan_path) else 0
        print("plan sentences=%d status=%s" % (n, result["status"]))
        return 0 if result["status"] != "failed" else 1

    print("case_id=%s status=%s edits=%d errors=%d" % (
        result["case_id"], result["status"],
        main_result.get("metrics", {}).get("edit_count", 0), len(r.get("errors", []))))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
