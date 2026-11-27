#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry for the bilingual translation skill.

Two-phase by design, because a deterministic script must not invent a
translation:

    # phase 1 -- produce the plan (segment ids, locked glossary, constraints)
    python scripts/run_case.py --plan-only

    # phase 2 -- validate the model-authored draft and write result.json
    python scripts/run_case.py --draft /app/work/draft.json

With no --draft the script still writes result.json (status=partial) plus
plan.json, so a caller that only runs it once gets a usable hand-off rather
than a fabricated translation.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skillkit as sk          # noqa: E402
import translate_guard as tg   # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default=None)
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--draft", default=None)
    ap.add_argument("--target-lang", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--plan-only", action="store_true")
    a = ap.parse_args(argv)

    case_path = a.case or os.path.join(a.input_dir, "case.json")
    case, case_path = sk.load_case(case_path)
    input_dir = a.input_dir if os.path.isdir(a.input_dir) else (os.path.dirname(case_path) or ".")
    out_dir = a.out
    work_dir = a.work
    for d in (out_dir, work_dir):
        if not os.path.isdir(d):
            os.makedirs(d)

    materials = sk.material_texts(case, case_path, input_dir)
    draft_path = None if a.plan_only else (a.draft or sk.find_draft(case, case_path, input_dir))
    r = tg.run(case, materials, out_dir, draft_path=draft_path,
               target_lang=a.target_lang, title=a.title)

    if a.plan_only:
        print("plan segments=%d" % len(r.get("plan", {}).get("segments", [])))

    main_result = r["main"]
    uncertainty = {
        "warnings": r.get("warnings", []),
        "human_review": [w for w in r.get("warnings", []) if w.get("code") in
                         ("hedge_lost", "number_added", "citation_localised",
                          "back_translation_diverges", "length_outlier")],
        "missing_fields": [],
        "note": ("deterministic guard: segment coverage, glossary enforcement, "
                 "numbers/citations/formulas, negation/hedge polarity. "
                 "Translation quality itself needs human review."),
    }
    if not draft_path:
        uncertainty["next_step"] = ("write /app/work/draft.json as "
                                    "{\"segments\":[{\"id\":\"p001\",\"target\":\"...\"}]} "
                                    "then rerun with --draft")
    result = sk.write_result(
        out_dir, "bilingual-translation-guard", "文献翻译（双语对照）", case, r["status"],
        main_result,
        evidence={"anchors": [{"segment": s["id"], "zone": s["zone"]} for s in
                              main_result.get("segments", [])],
                  "method": "paragraph ids + byte-level checks on numbers/citations/formulas"},
        uncertainty=uncertainty,
        sources=sk.sources_of(r.get("sources", [])),
        runs=[{"step": "translate_guard", "status": r["status"],
               "errors": len(r.get("errors", [])), "warnings": len(r.get("warnings", []))}],
    )
    lines = ["- status: **%s**" % result["status"],
             "- segments: %d, translated: %d" % (
                 len(main_result.get("segments", [])),
                 sum(1 for s in main_result.get("segments", []) if s.get("target"))),
             "- errors: %d, warnings: %d" % (len(r.get("errors", [])), len(r.get("warnings", [])))]
    for e in r.get("errors", [])[:10]:
        lines.append("- ERROR `%s` %s: %s" % (e.get("code"), e.get("id"), e.get("detail")))
    sk.write_report(out_dir, "translation / %s" % result["case_id"], lines)
    print("case_id=%s status=%s segments=%d errors=%d" % (
        result["case_id"], result["status"], len(main_result.get("segments", [])),
        len(r.get("errors", []))))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
