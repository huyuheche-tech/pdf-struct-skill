#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry for the reference / citation skill.

    # reconcile only: no manuscript is rewritten
    python scripts/run_case.py --check-only

    # full pass: reconcile, renumber, render the bibliography
    python scripts/run_case.py --draft /app/work/draft.json

The mechanical pass (parse, reconcile, renumber, render) always runs.  The
draft carries the editorial decisions a script must not invent: which extra
entries to merge, and which entries are claimed complete.  Without a draft the
result is `partial` and `uncertainty.next_step` says what is missing.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skillkit as sk       # noqa: E402
import cite_ledger as cl    # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default=None)
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--draft", default=None)
    ap.add_argument("--style", default=None, choices=["gbt7714", "apa"])
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args(argv)

    case_path = a.case or os.path.join(a.input_dir, "case.json")
    case, case_path = sk.load_case(case_path)
    input_dir = a.input_dir if os.path.isdir(a.input_dir) else (os.path.dirname(case_path) or ".")
    out_dir, work_dir = a.out, a.work
    for d in (out_dir, work_dir):
        if not os.path.isdir(d):
            os.makedirs(d)

    materials = sk.material_texts(case, case_path, input_dir)
    draft_path = None if a.check_only else (a.draft or sk.find_draft(case, case_path, input_dir))
    style = a.style or (case.get("style") if isinstance(case, dict) else None) or "gbt7714"

    r = cl.run(case, materials, out_dir, draft_path=draft_path, style=style,
               check_only=a.check_only)

    main_result = r["main"]
    warnings = r.get("warnings", [])
    uncertainty = {
        "warnings": warnings,
        "human_review": [w for w in warnings if w.get("code") in
                         ("uncited_entry", "missing_entry", "duplicate_entry",
                          "field_missing", "number_gap")],
        "missing_fields": sorted(set(w["key"] + "." + w["field"] for w in warnings
                                     if w.get("code") == "field_missing" and w.get("key"))),
        "note": ("deterministic pass: parsing, two-way reconciliation, first-appearance "
                 "renumbering, DOI/title de-duplication, GB/T 7714-2015 or APA rendering. "
                 "Whether a reference is real, and whether the cited claim matches the "
                 "source, needs human review."),
    }
    if r["status"] == "failed":
        uncertainty["next_step"] = ("no readable manuscript or bibliography under the input "
                                    "dir; provide .md/.txt text plus .bib/.ris/numbered list")
    elif a.check_only:
        uncertainty["next_step"] = ("check-only mode: the manuscript was not rewritten. "
                                    "Drop --check-only to get manuscript_renumbered.md.")
    elif not draft_path:
        uncertainty["next_step"] = (
            "write /app/work/draft.json as {\"merges\": [[\"keyA\",\"keyB\"]], "
            "\"declared_complete\": [\"keyA\"]} (empty lists are fine) then rerun "
            "with --draft; without it the merge/completeness decisions are not audited")

    result = sk.write_result(
        out_dir, "citation-ledger", "参考文献与引用管理（对账 + 重编号）", case, r["status"],
        main_result,
        evidence={"anchors": [{"citation": c["raw"], "keys": c["keys"]}
                              for c in main_result.get("checks", {}).get("citations", [])],
                  "method": "parsed entries + parsed in-text citations, matched both ways",
                  "style": style},
        uncertainty=uncertainty,
        sources=sk.sources_of(r.get("sources", [])),
        runs=[{"step": "cite_ledger", "status": r["status"],
               "errors": len(r.get("errors", [])), "warnings": len(warnings)}],
    )

    m = main_result.get("metrics", {})
    lines = ["- status: **%s**" % result["status"],
             "- entries: %s, cited: %s, uncited: %s, missing: %s, duplicates: %s"
             % (m.get("entries"), m.get("cited"), m.get("uncited"),
                m.get("missing"), m.get("duplicates")),
             "- field_completeness: %s" % m.get("field_completeness"),
             "- errors: %d, warnings: %d" % (len(r.get("errors", [])), len(warnings))]
    for e in r.get("errors", [])[:12]:
        lines.append("- ERROR `%s` %s" % (e.get("code"), e.get("detail")))
    sk.write_report(out_dir, "references / %s" % result["case_id"], lines)

    print("case_id=%s status=%s entries=%s cited=%s missing=%s errors=%d" % (
        result["case_id"], result["status"], m.get("entries"), m.get("cited"),
        m.get("missing"), len(r.get("errors", []))))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
