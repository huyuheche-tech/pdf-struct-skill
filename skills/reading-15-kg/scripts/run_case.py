#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry for the literature knowledge-graph skill.

    # phase 1 -- candidate entities from two papers (no graph is invented)
    python scripts/run_case.py --case /input/case.json --input-dir /input \
        --out /app/output --work /app/work

    # phase 2 -- validate a model-authored graph and emit the deliverables
    python scripts/run_case.py --case /input/case.json --input-dir /input \
        --out /app/output --work /app/work --draft /app/work/draft.json

    # incremental: keep the existing ids of a previously delivered graph
    python scripts/run_case.py ... --draft draft.json --base /app/work/base-graph.json

Without --draft the run still writes graph.json (candidates, candidate=true),
graph.csv, queries.md, checks.json and result.json, but status stays partial.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skillkit as sk          # noqa: E402
import kg_builder as kg        # noqa: E402


def safe(s):
    """stdout must stay ASCII; Chinese goes into files, not the console."""
    return str(s).encode("ascii", "replace").decode("ascii")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default=None)
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--draft", default=None, help="model-authored graph json")
    ap.add_argument("--base", default=None, help="existing graph.json for incremental mode")
    a = ap.parse_args(argv)

    case_path = a.case or os.path.join(a.input_dir, "case.json")
    case, case_path = sk.load_case(case_path)
    input_dir = a.input_dir if os.path.isdir(a.input_dir) else (os.path.dirname(case_path) or ".")
    for d in (a.out, a.work):
        if not os.path.isdir(d):
            os.makedirs(d)

    materials = sk.material_texts(case, case_path, input_dir)
    draft_path = a.draft or sk.find_draft(case, case_path, input_dir)
    draft = sk.load_draft(draft_path) if draft_path else None

    base_path = a.base or (case.get("base_graph") if isinstance(case, dict) else None)
    if not base_path and os.path.exists(os.path.join(a.work, "base-graph.json")):
        base_path = os.path.join(a.work, "base-graph.json")
    base = None
    if base_path and os.path.exists(base_path):
        try:
            base = sk.jload(base_path)
        except Exception:
            base = None

    r = kg.run(case, materials, a.out, draft=draft, base=base)
    if r["status"] == "failed":
        sk.write_report(a.out, "KG / no material", ["- status: **failed**",
                                                    "- 输入里没有可读的论文材料。"])
        result = sk.write_result(
            a.out, "literature-knowledge-graph", "文献知识图谱构建", case, "failed",
            {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
             "graph": {"nodes": [], "edges": []}, "queries": [],
             "checks": {"errors": [{"code": "no_material"}]},
             "metrics": {"nodes": 0, "edges": 0, "evidence_resolved": 0,
                         "merged": 0, "conflicts": 0, "queries": 0}, "files": {}},
            uncertainty={"warnings": [{"code": "no_material"}], "missing_fields": [],
                         "next_step": "把 corpus-manifest.json 与两篇正文放进 /input 后重跑"},
            sources=sk.sources_of([m["path"] for m in materials]))
        print("case_id=%s status=failed reason=no_material" % safe(result["case_id"]))
        return 1

    main = r["main"]
    main["case_id"] = sk.case_id_of(case, [m["path"] for m in materials])
    main["files"] = {"graph": "graph.json", "graph_csv": "graph.csv",
                     "queries": "queries.md", "checks": "checks.json"}
    errors = r["errors"]
    warnings = r["warnings"]
    metrics = main["metrics"]

    uncertainty = {
        "warnings": warnings,
        "human_review": [w for w in warnings if w["code"] in
                         ("name_conflict", "unmerged_duplicate", "orphan_node",
                          "incremental_conflict", "node_unevidenced")],
        "missing_fields": [],
        "note": ("evidence is resolved against JATS paragraph_id, not PDF pages; "
                 "merge policy and controlled relation vocabulary are enforced "
                 "deterministically. Candidate extraction without a draft is only a "
                 "starting point, not a graph."),
        "paragraph_scheme": "JATS paragraph_id (p1-3), not PDF page numbers",
        "papers": list(r["corpus"]["order"]),
    }
    if not draft:
        uncertainty["next_step"] = ("write /app/work/draft.json with nodes/edges/queries "
                                    "(every edge needs source_id + paragraph_id + quote) "
                                    "and rerun with --draft")
    elif errors:
        uncertainty["next_step"] = ("fix the %d errors in checks.json, then rerun"
                                    % len(errors))

    report_lines = ["- status: **%s**" % r["status"],
                    "- nodes: %d, edges: %d, queries: %d"
                    % (metrics["nodes"], metrics["edges"], metrics["queries"]),
                    "- evidence resolved: %d/%d" % (metrics["evidence_resolved"],
                                                    metrics["edges"]),
                    "- merged: %d, conflicts: %d" % (metrics["merged"], metrics["conflicts"])]
    for e in errors[:12]:
        report_lines.append("- ERROR `%s` %s: %s" % (e["code"], e.get("id"), e["detail"]))
    for w in warnings[:8]:
        report_lines.append("- WARN `%s` %s: %s" % (w["code"], w.get("id"), w["detail"]))
    if r.get("incremental"):
        inc = r["incremental"]
        report_lines.append("- incremental added nodes: %s" % ",".join(inc["added"]["nodes"]))
        report_lines.append("- incremental merged: %s"
                            % "; ".join("%s->%s" % (m["from"], m["into"]) for m in inc["merged"]))
        report_lines.append("- incremental conflicts: %s"
                            % "; ".join(c["id"] for c in inc["conflicting"]))
    sk.write_report(a.out, "knowledge graph / %s" % main["case_id"], report_lines)

    result = sk.write_result(
        a.out, "literature-knowledge-graph", "文献知识图谱构建", case, r["status"], main,
        evidence={"paragraphs": r.get("paragraphs_used", []),
                  "method": "quote resolution against cited paragraph; relation vocabulary; "
                            "merge policy; executed queries"},
        uncertainty=uncertainty,
        sources=sk.sources_of([m["path"] for m in materials]),
        runs=[{"step": "kg_builder", "status": r["status"], "errors": len(errors),
               "warnings": len(warnings), "nodes": metrics["nodes"],
               "edges": metrics["edges"], "queries": metrics["queries"]}])

    print("case_id=%s status=%s nodes=%d edges=%d queries=%d errors=%d warnings=%d"
          % (safe(result["case_id"]), result["status"], metrics["nodes"], metrics["edges"],
             metrics["queries"], len(errors), len(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
