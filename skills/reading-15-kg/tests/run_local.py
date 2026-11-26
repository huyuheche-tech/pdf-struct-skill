#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local self-test for the literature knowledge-graph skill.

Run:  python tests/run_local.py
These are synthetic two-paper corpora for pipeline testing only; they are NOT
the official platform cases.
"""
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
PY = sys.executable


def run_case(case_dir, draft=None, base=None):
    tmp = tempfile.mkdtemp(prefix="kg-")
    out = os.path.join(tmp, "out")
    work = os.path.join(tmp, "work")
    args = [os.path.join(case_dir, "case.json"), "--input-dir", case_dir,
            "--out", out, "--work", work]
    cmd = [PY, RUN, "--case"] + args
    if draft:
        cmd += ["--draft", draft]
    if base:
        cmd += ["--base", base]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    rp = os.path.join(out, "result.json")
    res = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None
    csv_path = os.path.join(out, "graph.csv")
    csv_text = open(csv_path, encoding="utf-8").read() if os.path.exists(csv_path) else ""
    return p, res, csv_text


def codes(res, key="errors"):
    if not res:
        return []
    return [e["code"] for e in res["main_result"]["checks"][key]]


def main():
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    d1 = os.path.join(CASES, "case-01")
    p, r, csv_text = run_case(d1, draft=os.path.join(d1, "draft.json"))
    add("case01.exit", p.returncode == 0, p.stdout.strip()[-300:])
    add("case01.success", r and r["status"] == "success", r["status"] if r else "no result")
    m1 = (r or {}).get("main_result", {}).get("metrics", {})
    add("case01.eight_nodes", m1.get("nodes") == 8, str(m1.get("nodes")))
    add("case01.ten_edges", m1.get("edges") == 10, str(m1.get("edges")))
    add("case01.evidence_all_resolved", m1.get("evidence_resolved") == 10,
        str(m1.get("evidence_resolved")))
    add("case01.no_errors", codes(r) == [], ",".join(codes(r)))
    qs = (r or {}).get("main_result", {}).get("queries", [])
    add("case01.three_queries_evidenced",
        len(qs) == 3 and all(q.get("evidence") for q in qs),
        ",".join("%s:%d" % (q["id"], len(q.get("evidence") or [])) for q in qs))
    add("case01.contract_filled",
        r and bool(r["output_contract"]) and all(v is not None for v in r["output_contract"].values()),
        json.dumps(r["output_contract"], ensure_ascii=False)[:200] if r else "")
    add("case01.csv_has_both_sections",
        "# section: nodes" in csv_text and "# section: edges" in csv_text, "")

    d2 = os.path.join(CASES, "case-02")
    p, r2, _c = run_case(d2, draft=os.path.join(d2, "draft.json"))
    e2 = codes(r2)
    add("case02.partial", r2 and r2["status"] == "partial", r2["status"] if r2 else "no result")
    for code in ("evidence_unresolved", "name_conflict", "query_unevidenced"):
        add("case02.detects_" + code, code in e2, ",".join(e2))

    d3 = os.path.join(CASES, "case-03")
    p, r3, _c = run_case(d3, draft=os.path.join(d3, "draft.json"),
                         base=os.path.join(d3, "base-graph.json"))
    add("case03.success", r3 and r3["status"] == "success", r3["status"] if r3 else "no result")
    ids = [n["id"] for n in (r3 or {}).get("main_result", {}).get("graph", {}).get("nodes", [])]
    add("case03.keeps_base_ids", all(x in ids for x in ("n1", "n2", "n3", "n4", "n5")),
        ",".join(ids))
    inc = (r3 or {}).get("main_result", {}).get("checks", {}).get("incremental") or {}
    add("case03.one_added_merged_conflict",
        inc.get("added", {}).get("nodes") == ["n9"]
        and len(inc.get("merged") or []) == 1 and len(inc.get("conflicting") or []) == 1,
        json.dumps({"added": inc.get("added"), "merged": len(inc.get("merged") or []),
                    "conflicting": len(inc.get("conflicting") or [])}, ensure_ascii=False))

    # negative 1: two papers' numbers fused into one comparative edge
    tmp = tempfile.mkdtemp(prefix="kg-bad-")
    payload = json.load(open(os.path.join(d1, "draft.json"), encoding="utf-8"))
    for e in payload["edges"]:
        if e["id"] == "e10":
            e["relation"] = "outperforms"
            e["conditions"] = ""
    bad = os.path.join(tmp, "draft.json")
    json.dump(payload, open(bad, "w", encoding="utf-8"), ensure_ascii=False)
    p, rb, _c = run_case(d1, draft=bad)
    add("negative.cross_paper_overreach", "cross_paper_overreach" in codes(rb), ",".join(codes(rb)))

    # negative 2: drop paragraph_id from an edge
    payload2 = json.load(open(os.path.join(d1, "draft.json"), encoding="utf-8"))
    for e in payload2["edges"]:
        if e["id"] == "e1":
            e.pop("paragraph_id", None)
    bad2 = os.path.join(tmp, "draft2.json")
    json.dump(payload2, open(bad2, "w", encoding="utf-8"), ensure_ascii=False)
    p, rc, _c = run_case(d1, draft=bad2)
    add("negative.missing_paragraph_id", "evidence_unresolved" in codes(rc), ",".join(codes(rc)))

    # negative 3: no draft at all -> partial with candidate nodes, never a graph
    nod = tempfile.mkdtemp(prefix="kg-nodraft-")
    for name in ("case.json", "material.json", "corpus-manifest.json",
                 "primary-material.json", "secondary-material.json"):
        shutil.copy(os.path.join(d1, name), os.path.join(nod, name))
    p, rn, _c = run_case(nod)
    nodes = (rn or {}).get("main_result", {}).get("graph", {}).get("nodes", [])
    add("negative.no_draft_is_partial",
        rn and rn["status"] == "partial" and nodes and all(n.get("candidate") for n in nodes),
        "%s nodes=%d" % ((rn or {}).get("status"), len(nodes)))

    failed = [c for c in checks if not c["ok"]]
    out_dir = os.path.join(ROOT, "results")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    json.dump({"checks": checks, "failed": len(failed),
               "note": "local self-test only; not the official platform cases"},
              open(os.path.join(out_dir, "local-eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"]
              + (" | " + c["detail"] if not c["ok"] else ""))
    print("%d checks, %d failed" % (len(checks), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
