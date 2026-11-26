#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry for the methods / experiments skill.

Two phases, because a deterministic script must not invent methods prose:

    # phase 1 -- flatten config/log into a parameter ledger
    python scripts/run_case.py --plan-only

    # phase 2 -- validate the model-authored draft and write result.json
    python scripts/run_case.py --draft /app/work/draft.json

With no --draft the script still writes params.json and result.json
(status=partial) with a next_step instruction, never a fabricated methods text.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skillkit as sk         # noqa: E402
import methods_ledger as ml   # noqa: E402


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

    materials = sk.material_texts(case, case_path, input_dir,
                                  exts=sk.TEXT_EXT + sk.PDF_EXT + (".log",))
    draft_path = a.draft or sk.find_draft(case, case_path, input_dir)
    r = ml.run(case, materials, out_dir, draft_path=draft_path)

    if a.plan_only:
        sk.ascii_print("params=%d" % len(r["main"].get("tables", [])))
        return 0

    main_result = r["main"]
    uncertainty = {
        "warnings": r.get("warnings", []),
        "gaps": r.get("gaps", []),
        "human_review": [],
        "missing_fields": [],
        "note": ("deterministic ledger: parameter provenance, number-to-source, "
                 "six-element coverage, reproducibility checklist, baseline and "
                 "dataset specification. It does not judge prose quality."),
    }
    if not r.get("has_draft"):
        uncertainty["next_step"] = (
            "write /app/work/draft.json as {\"methods\":\"...\"} (or with a "
            "\"params\":[{\"name\":...,\"value\":...}] ledger) then rerun with --draft")
    result = sk.write_result(
        out_dir, "methods-parameter-ledger", "方法与实验章节（参数台账）", case, r["status"],
        main_result,
        evidence={"anchors": [{"param": p["name"], "source": p["source"]}
                              for p in main_result.get("tables", [])],
                  "method": "config/log flattening + number provenance + checklist"},
        uncertainty=uncertainty,
        sources=sk.sources_of(r.get("sources", [])),
        runs=[{"step": "methods_ledger", "status": r["status"],
               "errors": len(r.get("errors", [])), "warnings": len(r.get("warnings", [])),
               "gaps": len(r.get("gaps", []))}],
    )
    lines = ["- status: **%s**" % result["status"],
             "- parameters: %d" % len(main_result.get("tables", [])),
             "- errors: %d, warnings: %d, gaps: %d" % (
                 len(r.get("errors", [])), len(r.get("warnings", [])), len(r.get("gaps", [])))]
    for e in r.get("errors", [])[:10]:
        lines.append("- ERROR `%s` %s: %s" % (e.get("code"),
                                               e.get("category") or e.get("item") or "",
                                               e.get("detail")))
    sk.write_report(out_dir, "methods / %s" % result["case_id"], lines)
    sk.ascii_print("case_id=%s status=%s params=%d errors=%d" % (
        result["case_id"], result["status"], len(main_result.get("tables", [])),
        len(r.get("errors", []))))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
