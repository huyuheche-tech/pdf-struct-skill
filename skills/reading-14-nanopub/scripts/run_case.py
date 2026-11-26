#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry for the nanopublication assertion skill.

    # phase 1 -- clause-level candidate assertions (unverified, partial)
    python scripts/run_case.py --outline

    # phase 2 -- validate the model-authored assertions and export nanopub.json
    python scripts/run_case.py --draft /app/work/draft.json

Both phases write result.json.  Without a draft the status is ``partial`` and
``uncertainty.next_step`` says what to write; the script never invents claims.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skillkit as sk            # noqa: E402
import nanopub_builder as npb   # noqa: E402


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
                                          names=("draft.json", "assertions.json", "answer.json")))
    r = npb.run(case, materials, a.out, draft_path=draft_path, title=a.title)

    if a.outline:
        sk.ascii_print("assertions=%d candidate=%s" % (
            len((r.get("main") or {}).get("assertions", [])), r.get("candidate")))

    if r.get("fatal"):
        # no readable material: write a failed envelope, never a fake assertion
        main_result = {"case_id": sk.case_id_of(case, []), "assertions": [], "nanopub": {},
                       "checks": {"errors": r["fatal"], "warnings": []},
                       "metrics": {"assertions": 0, "evidence_resolved": 0,
                                   "atomic": 0, "overbroad": 0, "duplicates": 0}}
        result = sk.write_result(
            a.out, "nanopub-assertion-builder", "Nanopublication 断言", case, "failed",
            main_result,
            evidence={"anchors": [], "method": "no material"},
            uncertainty={"warnings": [{"code": "no_material"}],
                         "human_review": [], "missing_fields": [],
                         "note": "no readable text material; nothing was asserted",
                         "next_step": "provide a text-layer PDF, markdown or txt file and rerun"},
            sources=[], runs=[{"step": "nanopub_builder", "status": "failed"}])
        sk.write_report(a.out, "nanopub / %s" % result["case_id"],
                        ["- status: **failed**", "- no readable material"])
        sk.ascii_print("case_id=%s status=failed assertions=0" % result["case_id"])
        return 1

    main_result = r["main"]
    uncertainty = {
        "warnings": r.get("warnings", []),
        "human_review": [w for w in r.get("warnings", [])
                         if w.get("code") in ("candidate_assertions", "draft_unreadable",
                                              "evidence_elsewhere", "no_assertions")],
        "missing_fields": sorted({e.get("code") for e in r.get("errors", [])
                                  if e.get("code") in ("triple_incomplete", "source_missing")}),
        "note": ("deterministic checks: evidence quote in the cited paragraph, atomicity, "
                 "condition retention, over-broad wording, duplicates, controlled predicates. "
                 "Whether the assertion is scientifically right still needs a human."),
    }
    if not draft_path:
        uncertainty["next_step"] = (
            "write /app/work/draft.json as {\"assertions\":[{\"id\":\"a1\",\"text\":\"...\","
            "\"subject\":\"...\",\"predicate\":\"supports|contradicts|uses|compares|"
            "has_property|measured_by|part_of\",\"object\":\"...\",\"conditions\":\"...\","
            "\"evidence\":\"<short quote>\",\"source_id\":\"...\",\"paragraph_id\":\"s02.p01\","
            "\"confidence\":\"high|medium|low\"}]} then rerun with --draft")

    result = sk.write_result(
        a.out, "nanopub-assertion-builder", "Nanopublication 断言", case, r["status"],
        main_result,
        evidence={"anchors": [{"id": x.get("id"), "paragraph_id": x.get("paragraph_id")}
                              for x in main_result.get("assertions", [])],
                  "method": "sNN.pMM paragraph ids + exact evidence resolution + controlled predicates"},
        uncertainty=uncertainty,
        sources=sk.sources_of(r.get("sources", [])),
        runs=[{"step": "nanopub_builder", "status": r["status"],
               "errors": len(r.get("errors", [])), "warnings": len(r.get("warnings", []))}],
    )
    mt = main_result.get("metrics", {})
    lines = ["- status: **%s**" % result["status"],
             "- assertions: %s, evidence_resolved: %s" % (
                 mt.get("assertions"), mt.get("evidence_resolved")),
             "- atomic: %s, overbroad: %s, duplicates: %s" % (
                 mt.get("atomic"), mt.get("overbroad"), mt.get("duplicates")),
             "- errors: %d, warnings: %d" % (len(r.get("errors", [])), len(r.get("warnings", [])))]
    for e in r.get("errors", [])[:10]:
        lines.append("- ERROR `%s` %s: %s" % (e.get("code"), e.get("id"), e.get("detail")))
    sk.write_report(a.out, "nanopub / %s" % result["case_id"], lines)
    sk.ascii_print("case_id=%s status=%s assertions=%s errors=%d" % (
        result["case_id"], result["status"], mt.get("assertions"), len(r.get("errors", []))))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
