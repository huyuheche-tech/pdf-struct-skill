#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry for the introduction / related-work skill.

Two phases, because the deterministic engine must not write the prose:

    # phase 1 -- build the evidence table and the writing brief
    python scripts/run_case.py --plan-only

    # phase 2 -- validate the model-authored draft and write result.json
    python scripts/run_case.py --draft /app/work/draft.json

With no --draft the script still emits evidence.json and result.json
(status=partial) with a next_step instruction, never a fabricated introduction.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skillkit as sk          # noqa: E402
import intro_builder as ib     # noqa: E402


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

    if a.title and isinstance(case, dict):
        case = dict(case)
        case.setdefault("title", a.title)

    materials = sk.material_texts(case, case_path, input_dir)
    draft_path = None if a.plan_only else (a.draft or sk.find_draft(case, case_path, input_dir))
    r = ib.run(case, materials, out_dir, draft_path=draft_path)

    if a.plan_only:
        sk.ascii_print("evidence sentences=%d" % len(r["main"].get("evidence", [])))

    main_result = r["main"]
    uncertainty = {
        "warnings": r.get("warnings", []),
        "human_review": [w for w in r.get("warnings", []) if w.get("code") in
                         ("anchor_unlisted", "citation_unverified")],
        "missing_fields": [],
        "note": ("deterministic binder: four-section completeness, number-to-evidence, "
                 "contribution-to-quote, gap citation strength, related-work grouping, "
                 "citation key existence. It does not judge prose quality."),
    }
    if not r.get("has_draft"):
        uncertainty["next_step"] = (
            "write /app/work/draft.json as {\"sections\":{\"background\":\"...\","
            "\"related_work\":\"...\",\"gap\":\"...\",\"contributions\":[\"...\"]},"
            "\"contribution_evidence\":[{\"contribution\":1,\"anchor\":\"p001.s02\","
            "\"quote\":\"...\"}],\"groups\":[{\"label\":\"group-a\",\"works\":[\"key1\"]}]}"
            " then rerun with --draft")
    result = sk.write_result(
        out_dir, "intro-evidence-binder", "引言与相关工作（证据绑定）", case, r["status"],
        main_result,
        evidence={"anchors": [{"anchor": e["anchor"]} for e in main_result.get("evidence", [])],
                  "method": "stable sentence anchors + number multiset + quote re-resolution"},
        uncertainty=uncertainty,
        sources=sk.sources_of(r.get("sources", [])),
        runs=[{"step": "intro_builder", "status": r["status"],
               "errors": len(r.get("errors", [])), "warnings": len(r.get("warnings", []))}],
    )
    lines = ["- status: **%s**" % result["status"],
             "- evidence sentences: %d" % len(main_result.get("evidence", [])),
             "- errors: %d, warnings: %d" % (len(r.get("errors", [])), len(r.get("warnings", [])))]
    for e in r.get("errors", [])[:10]:
        lines.append("- ERROR `%s` %s: %s" % (e.get("code"),
                                               e.get("section") or e.get("contribution") or "",
                                               e.get("detail")))
    sk.write_report(out_dir, "introduction / %s" % result["case_id"], lines)
    sk.ascii_print("case_id=%s status=%s evidence=%d errors=%d" % (
        result["case_id"], result["status"], len(main_result.get("evidence", [])),
        len(r.get("errors", []))))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
