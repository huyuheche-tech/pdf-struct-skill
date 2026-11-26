#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local self-test for the nanopublication skill. Not the official platform cases."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN = os.path.join(ROOT, "scripts", "run_case.py")
CASES = os.path.join(HERE, "cases")


def run_case(case_dir, draft=None):
    tmp = tempfile.mkdtemp(prefix="np-")
    out = os.path.join(tmp, "out")
    work = os.path.join(tmp, "work")
    cmd = [sys.executable, RUN, "--case", os.path.join(case_dir, "case.json"),
           "--input-dir", case_dir, "--out", out, "--work", work]
    if draft:
        cmd += ["--draft", draft]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    rp = os.path.join(out, "result.json")
    res = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None
    return p, res, out


def _a(s):
    return str(s).encode("ascii", "replace").decode("ascii")


def codes(res):
    if not res:
        return []
    return [e["code"] for e in res["main_result"]["checks"]["errors"]]


def metrics(res):
    return (res or {}).get("main_result", {}).get("metrics", {})


def main():
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    d1 = os.path.join(CASES, "case-01")
    p, r, out = run_case(d1, os.path.join(d1, "draft.json"))
    add("case01.exit", p.returncode == 0, p.stdout.strip()[-200:])
    add("case01.success", r and r["status"] == "success", r["status"] if r else "no result")
    add("case01.no_errors", codes(r) == [], ",".join(codes(r)))
    add("case01.assertions_4", metrics(r).get("assertions") == 4,
        json.dumps(metrics(r), ensure_ascii=False))
    add("case01.evidence_all_resolved", metrics(r).get("evidence_resolved") == 4,
        json.dumps(metrics(r), ensure_ascii=False))
    add("case01.atomic_all", metrics(r).get("atomic") == 4,
        json.dumps(metrics(r), ensure_ascii=False))
    add("case01.contract_filled",
        r and all(v is not None for v in r["output_contract"].values()),
        json.dumps((r or {}).get("output_contract", {}), ensure_ascii=False)[:160])
    np = (r or {}).get("main_result", {}).get("nanopub", {})
    ok_parts = (set(np.keys()) >= {"assertion", "provenance", "pubinfo"}
                and np.get("pubinfo", {}).get("license") == "CC-BY-4.0"
                and np.get("pubinfo", {}).get("template") == "nano-pub/1"
                and all(a.get("uri", "").startswith("urn:nanopub:")
                        for a in np.get("assertion", {}).get("assertions", [])))
    add("case01.nanopub_three_parts", ok_parts, json.dumps(np, ensure_ascii=False)[:160])
    add("case01.provenance_spans",
        bool(np.get("provenance")) and all(pv.get("char_span") for pv in np["provenance"]),
        json.dumps(np.get("provenance", []), ensure_ascii=False)[:160])
    need = ("nanopub.json", "assertions.md", "checks.json", "sections.json", "result.json")
    add("case01.outputs_exist", all(os.path.exists(os.path.join(out, n)) for n in need),
        ",".join(n for n in need if not os.path.exists(os.path.join(out, n))))

    d2 = os.path.join(CASES, "case-02")
    p, r2, _o2 = run_case(d2, os.path.join(d2, "draft.json"))
    c2 = codes(r2)
    add("case02.partial", r2 and r2["status"] == "partial", r2["status"] if r2 else "no result")
    for code in ("not_atomic", "evidence_unresolved", "overbroad"):
        add("case02.detects_" + code, code in c2, ",".join(c2))

    d3 = os.path.join(CASES, "case-03")
    p, r3, _o3 = run_case(d3, os.path.join(d3, "draft.json"))
    add("case03.success", r3 and r3["status"] == "success", r3["status"] if r3 else "no result")
    add("case03.no_errors", codes(r3) == [], ",".join(codes(r3)))
    subs = [a.get("subject") for a in (r3 or {}).get("main_result", {}).get("assertions", [])]
    add("case03.chinese_assertions", subs == ["校准层"] * 3, json.dumps(subs, ensure_ascii=False))

    # no draft -> partial with next_step, never success
    nodraft = tempfile.mkdtemp(prefix="np-nodraft-")
    for name in ("case.json", "material.md"):
        with open(os.path.join(d1, name), "rb") as fh:
            open(os.path.join(nodraft, name), "wb").write(fh.read())
    p, r4, _o4 = run_case(nodraft, None)
    add("nodraft.partial", r4 and r4["status"] == "partial", r4["status"] if r4 else "no result")
    add("nodraft.next_step", bool((r4 or {}).get("uncertainty", {}).get("next_step")),
        str((r4 or {}).get("uncertainty", {}).get("next_step"))[:120])

    # no readable material -> failed
    empty = tempfile.mkdtemp(prefix="np-empty-")
    p, r5, _o5 = run_case(empty, None)
    add("nomaterial.failed", r5 and r5["status"] == "failed", r5["status"] if r5 else "no result")

    # negative 1: dropping the condition on a conditional claim must be caught
    bad = os.path.join(tempfile.mkdtemp(prefix="np-bad-"), "draft.json")
    payload = json.load(open(os.path.join(d1, "draft.json"), encoding="utf-8"))
    for a in payload["assertions"]:
        if a["id"] == "a2":
            a["conditions"] = ""
    json.dump(payload, open(bad, "w", encoding="utf-8"), ensure_ascii=False)
    p, r6, _o6 = run_case(d1, bad)
    add("negative.condition_dropped", r6 and "condition_dropped" in codes(r6),
        ",".join(codes(r6)))

    # negative 2: a predicate outside the controlled vocabulary must be rejected
    bad2 = os.path.join(tempfile.mkdtemp(prefix="np-bad2-"), "draft.json")
    payload = json.load(open(os.path.join(d1, "draft.json"), encoding="utf-8"))
    payload["assertions"][0]["predicate"] = "improves"
    json.dump(payload, open(bad2, "w", encoding="utf-8"), ensure_ascii=False)
    p, r7, _o7 = run_case(d1, bad2)
    add("negative.predicate_invalid", r7 and "predicate_invalid" in codes(r7),
        ",".join(codes(r7)))

    failed = [c for c in checks if not c["ok"]]
    out_dir = os.path.join(ROOT, "results")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    json.dump({"checks": checks, "failed": len(failed),
               "note": "local self-test only; not the official platform cases"},
              open(os.path.join(out_dir, "local-eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] +
              (" | " + _a(c["detail"]) if not c["ok"] else ""))
    print("%d checks, %d failed" % (len(checks), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
