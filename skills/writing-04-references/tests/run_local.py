#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local self-test for the reference / citation skill. Not the official cases."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(ROOT, "scripts", "run_case.py")
CASES = os.path.join(HERE, "cases")


def run_case(case_dir, draft, extra=None):
    tmp = tempfile.mkdtemp(prefix="rf-")
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
    return [e["code"] for e in res["main_result"]["checks"]["errors"]] if res else []


def warn_codes(res):
    return [w["code"] for w in res["main_result"]["checks"]["warnings"]] if res else []


def make_case(bib_text, manuscript_text, draft_obj, case_id="tmp"):
    d = tempfile.mkdtemp(prefix="rf-case-")
    open(os.path.join(d, "refs.bib"), "w", encoding="utf-8").write(bib_text)
    open(os.path.join(d, "manuscript.md"), "w", encoding="utf-8").write(manuscript_text)
    json.dump({"case_id": case_id, "library": "refs.bib", "manuscript": "manuscript.md",
               "output_contract": ["references", "renumber_map", "checks", "metrics", "status"]},
              open(os.path.join(d, "case.json"), "w", encoding="utf-8"), ensure_ascii=False)
    dp = os.path.join(d, "draft.json")
    json.dump(draft_obj, open(dp, "w", encoding="utf-8"), ensure_ascii=False)
    return d, dp


def main():
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    # ---------------- case 01: reconciliation ----------------
    d1 = os.path.join(CASES, "case-01")
    p, r, out = run_case(d1, os.path.join(d1, "draft.json"))
    add("case01.exit", p.returncode == 0, p.stdout.strip()[-200:])
    add("case01.partial", r and r["status"] == "partial", r["status"] if r else "no result")
    add("case01.missing_entry", "missing_entry" in err_codes(r), ",".join(err_codes(r)))
    add("case01.uncited_entry", "uncited_entry" in warn_codes(r), ",".join(warn_codes(r)))
    add("case01.contract_filled",
        r and all(v is not None for v in r["output_contract"].values()),
        json.dumps(r["output_contract"], ensure_ascii=False)[:160] if r else "")
    add("case01.files_written",
        os.path.exists(os.path.join(out, "bibliography.md"))
        and os.path.exists(os.path.join(out, "references.json"))
        and os.path.exists(os.path.join(out, "checks.json")), "")
    add("case01.manuscript_kept",
        r and "[2,4]" in r["main_result"]["manuscript_renumbered"], "")
    add("case01.cjk_authors_et_al",
        r and "等." in r["main_result"]["bibliography"], "")

    # ---------------- case 02: duplicate merge + renumber ----------------
    d2 = os.path.join(CASES, "case-02")
    p, r, _ = run_case(d2, os.path.join(d2, "draft.json"))
    m2 = (r or {}).get("main_result", {}).get("metrics", {})
    add("case02.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case02.duplicates_1", m2.get("duplicates") == 1, str(m2.get("duplicates")))
    add("case02.entries_after_merge", m2.get("entries") == 4, str(m2.get("entries")))
    add("case02.nothing_uncited", m2.get("uncited") == 0, str(m2.get("uncited")))
    add("case02.renumber_by_first_use",
        r and r["main_result"]["manuscript_renumbered"].count("[1]") == 1
        and "[3]" in r["main_result"]["manuscript_renumbered"], "")
    ren = (r or {}).get("main_result", {}).get("renumber_map", [])
    merged = [x for x in ren if x.get("merged_into")]
    add("case02.merge_recorded", bool(merged) and merged[0]["new"] is not None,
        json.dumps(merged, ensure_ascii=False)[:150])
    mg = (r or {}).get("main_result", {}).get("merges", [])
    add("case02.merge_basis_doi", bool(mg) and mg[0].get("basis") == "doi",
        json.dumps(mg, ensure_ascii=False)[:150])

    # APA is a different renderer over the same parsed entries
    p, r, _ = run_case(d2, os.path.join(d2, "draft.json"), ["--style", "apa"])
    add("case02.apa_style", r and "https://doi.org/" in r["main_result"]["bibliography"],
        "")
    add("case02.contract_filled",
        r and not r["contract_unresolved"]
        and all(v is not None for v in r["output_contract"].values()),
        json.dumps((r or {}).get("output_contract", {}), ensure_ascii=False)[:160])

    # ---------------- case 03: numbered txt + author-year ----------------
    d3 = os.path.join(CASES, "case-03")
    p, r, _ = run_case(d3, os.path.join(d3, "draft.json"))
    m3 = (r or {}).get("main_result", {}).get("metrics", {})
    add("case03.exit", p.returncode == 0, p.stdout.strip()[-200:])
    add("case03.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case03.all_cited", m3.get("cited") == 3 and m3.get("uncited") == 0,
        json.dumps(m3, ensure_ascii=False))
    add("case03.todo_for_missing_doi",
        r and r["main_result"]["bibliography"].count("[TODO: doi]") == 3, "")
    add("case03.author_year_untouched",
        r and "(Chen, 2019)" in r["main_result"]["manuscript_renumbered"], "")
    add("case03.completeness_flags",
        r and all("doi" in x["todo"] and x["completeness"]["title"]
                  for x in r["main_result"]["references"]), "")

    # ---------------- negative 1: unsafe merge of two real papers ----------------
    bib = """@article{chen2019a, author={Wei Chen}, title={Attention improves sample efficiency},
  journal={JMLR}, year={2019}, volume={20}, number={4}, pages={1--25}, doi={10.1000/a1}}
@article{chen2021b, author={Wei Chen}, title={Sparse attention for long documents},
  journal={TACL}, year={2021}, volume={9}, number={2}, pages={5--19}, doi={10.1000/b2}}
"""
    man = "Attention helps [1]. Sparse attention scales [2].\n"
    d, dp = make_case(bib, man, {"merges": [["chen2019a", "chen2021b"]],
                                 "declared_complete": []})
    p, r, _ = run_case(d, dp)
    add("negative.unsafe_merge", r and "unsafe_merge" in err_codes(r), ",".join(err_codes(r)))
    add("negative.unsafe_merge_refused",
        r and r["main_result"]["metrics"]["duplicates"] == 0,
        str((r or {}).get("main_result", {}).get("metrics", {}).get("duplicates")))

    # ---------------- negative 2: claim complete after the DOI is gone ----------
    bib2 = open(os.path.join(d2, "refs.bib"), encoding="utf-8").read()
    bib2 = re.sub(r"\n\s*doi\s*=\s*\{[^}]*\}", "", bib2)
    d, dp = make_case(bib2, open(os.path.join(d2, "manuscript.md"), encoding="utf-8").read(),
                      {"merges": [["chen2019conf", "chen2019j"]],
                       "declared_complete": ["chen2019j"]})
    p, r, _ = run_case(d, dp)
    fm = [e for e in (r or {}).get("main_result", {}).get("checks", {}).get("errors", [])
          if e["code"] == "field_missing"]
    add("negative.field_missing_when_claimed",
        bool(fm) and any(e.get("severity") == "error" and e.get("field") == "doi" for e in fm),
        ",".join(err_codes(r)))
    add("negative.field_missing_partial", r and r["status"] == "partial",
        r["status"] if r else "no result")

    # ---------------- negative 3: check-only must not rewrite ----------------
    p, r, out = run_case(d2, None, ["--check-only"])
    add("negative.check_only_no_rewrite",
        not os.path.exists(os.path.join(out, "manuscript_renumbered.md")), "")
    add("negative.check_only_not_success", r and r["status"] != "success",
        r["status"] if r else "no result")
    add("negative.check_only_next_step", r and bool(r["uncertainty"].get("next_step")), "")

    # ---------------- \cite keys survive, ranges are compressed ----------------
    bib4 = "".join(
        "@article{k%d, author={Wei Chen and Lin Zhao}, title={Paper number %d on attention},\n"
        "  journal={JMLR}, year={2019}, volume={20}, number={4}, pages={%d--%d}, "
        "doi={10.1000/x%d}}\n" % (i, i, i * 10, i * 10 + 9, i) for i in range(1, 5))
    d, dp = make_case(bib4, "First [4]. Then \\cite{k1,k2} and [1,2,3].\n",
                      {"merges": [], "declared_complete": ["k1", "k2", "k3", "k4"]})
    p, r, _ = run_case(d, dp)
    txt = (r or {}).get("main_result", {}).get("manuscript_renumbered", "")
    add("latex_cite_untouched", "\\cite{k1,k2}" in txt, txt[:120])
    add("range_renumbered_compressed", "[2-4]" in txt, txt[:120])
    add("no_false_merge_on_digits",
        (r or {}).get("main_result", {}).get("metrics", {}).get("duplicates") == 0,
        str((r or {}).get("main_result", {}).get("metrics", {}).get("duplicates")))

    # ---------------- no draft at all (a platform run that never wrote one) ----
    nd = tempfile.mkdtemp(prefix="rf-nodraft-")
    for name in ("case.json", "refs.bib", "manuscript.md"):
        shutil.copy(os.path.join(d1, name), os.path.join(nd, name))
    p, r, _ = run_case(nd, None)
    add("negative.no_draft_partial", r and r["status"] == "partial",
        r["status"] if r else "no result")
    add("negative.no_draft_next_step", r and bool(r["uncertainty"].get("next_step")), "")

    # ---------------- no material at all ----------------
    empty = tempfile.mkdtemp(prefix="rf-empty-")
    p, r, _ = run_case(empty, None)
    add("negative.no_manuscript_failed", r and r["status"] == "failed",
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
