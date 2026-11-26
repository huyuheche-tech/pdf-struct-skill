#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry for the structured paper notes skill.

    # phase 1 -- section/paragraph index plus a candidate card (unverified)
    python scripts/run_case.py --outline

    # phase 2 -- validate the model-authored note card and write the notes
    python scripts/run_case.py --draft /app/work/draft.json

Both phases write result.json.  Without a draft the status is ``partial`` and
``uncertainty.next_step`` says what to write; a deterministic script must not
pretend it has read the paper.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skillkit as sk          # noqa: E402
import notes_builder as nb     # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default=None)
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--draft", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--outline", action="store_true")
    a = ap.parse_args(argv)

    case_path = a.case or os.path.join(a.input_dir, "case.json")
    case, case_path = sk.load_case(case_path)
    input_dir = a.input_dir if os.path.isdir(a.input_dir) else (os.path.dirname(case_path) or ".")
    for d in (a.out, a.work):
        if not os.path.isdir(d):
            os.makedirs(d)

    materials = sk.material_texts(case, case_path, input_dir)
    draft_path = a.draft or (None if a.outline else sk.find_draft(case, case_path, input_dir,
                                          names=("draft.json", "notes.json", "answer.json")))
    r = nb.run(case, materials, a.out, draft_path=draft_path, title=a.title)

    if a.outline:
        sk.ascii_print("sections=%d candidate=%s" % (len(r.get("sections", [])), r.get("candidate")))

    main_result = r["main"]
    uncertainty = {
        "warnings": r.get("warnings", []),
        "human_review": [w for w in r.get("warnings", [])
                         if w.get("code") in ("candidate_card", "draft_unreadable",
                                              "section_unknown")],
        "missing_fields": sorted({e.get("field") for e in r.get("errors", [])
                                  if e.get("code") == "field_missing" and e.get("field")}),
        "note": ("deterministic checks: section coverage, per-field anchors resolved "
                 "against the paragraph text, findings/limitations counts, knowledge-point "
                 "de-duplication. Whether the note is a good summary still needs a human."),
    }
    if not draft_path:
        uncertainty["next_step"] = (
            "write /app/work/draft.json as "
            "{\"card\":{\"research_question\":{\"text\":\"...\",\"anchor\":\"s01.p01\","
            "\"quote\":\"...\"},\"data\":{...},\"method\":{...},"
            "\"findings\":[{...},{...}],\"limitations\":[{...}]},"
            "\"section_summaries\":[{\"section_id\":\"s01\",\"text\":\"...\","
            "\"anchor\":\"s01.p01\",\"quote\":\"...\"}],"
            "\"knowledge_points\":[{\"text\":\"...\",\"anchor\":\"s02.p01\",\"quote\":\"...\"}]} "
            "then rerun with --draft")

    result = sk.write_result(
        a.out, "structured-paper-notes", "文献总结与结构化笔记", case, r["status"],
        main_result,
        evidence={"anchors": [{"section": s["id"], "paragraphs": len(s["paragraphs"])}
                              for s in main_result.get("sections", [])],
                  "method": "sNN.pMM paragraph ids + exact quote resolution"},
        uncertainty=uncertainty,
        sources=sk.sources_of(r.get("sources", [])),
        runs=[{"step": "notes_builder", "status": r["status"],
               "errors": len(r.get("errors", [])), "warnings": len(r.get("warnings", []))}],
    )
    mt = main_result.get("metrics", {})
    lines = ["- status: **%s**" % result["status"],
             "- sections: %s, covered: %s" % (mt.get("sections"), mt.get("covered")),
             "- fields_complete: %s, anchors_resolved: %s, duplicates: %s" % (
                 mt.get("fields_complete"), mt.get("anchors_resolved"), mt.get("duplicates")),
             "- errors: %d, warnings: %d" % (len(r.get("errors", [])), len(r.get("warnings", [])))]
    for e in r.get("errors", [])[:10]:
        lines.append("- ERROR `%s` %s: %s" % (e.get("code"), e.get("field") or "",
                                              e.get("detail")))
    sk.write_report(a.out, "notes / %s" % result["case_id"], lines)
    sk.ascii_print("case_id=%s status=%s sections=%s covered=%s errors=%d" % (
        result["case_id"], result["status"], mt.get("sections"), mt.get("covered"),
        len(r.get("errors", []))))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
