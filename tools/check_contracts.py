# -*- coding: utf-8 -*-
"""Run case-01 of every skill and assert the contract values are real values."""
import glob
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SKILLS = ["reading-01-pdf", "reading-03-translation", "writing-02-polish",
          "writing-04-references", "writing-08-intro", "writing-09-methods",
          "reading-10-notes", "reading-14-nanopub", "writing-13-latex",
          "reading-15-kg"]
DRAFTS = ("draft.json", "draft.tex", "answer.json", "edits.json",
          "graph.json", "assertions.json", "translations.json")


def main():
    bad = 0
    for name in SKILLS:
        d = os.path.join(HERE, name)
        cdir = os.path.join(d, "tests", "cases", "case-01")
        case = json.load(io.open(os.path.join(cdir, "case.json"), encoding="utf-8"))
        tmp = tempfile.mkdtemp(prefix="ct-")
        out = os.path.join(tmp, "out")
        input_dir = cdir
        if os.path.isdir(os.path.join(d, "tests", "fixtures")):
            input_dir = os.path.join(d, "tests", "fixtures")
        cmd = [PY, os.path.join(d, "scripts", "run_case.py"),
               "--case", os.path.join(cdir, "case.json"), "--input-dir", input_dir,
               "--out", out, "--work", os.path.join(tmp, "work")]
        for n in DRAFTS:
            p = os.path.join(cdir, n)
            if os.path.isfile(p):
                cmd += ["--draft", p]
                break
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
        rp = os.path.join(out, "result.json")
        issues = []
        if not os.path.exists(rp):
            issues.append("no result.json (exit %d): %s" % (p.returncode,
                                                           (p.stderr or "")[-200:]))
        else:
            r = json.load(io.open(rp, encoding="utf-8"))
            fields = r.get("output_contract_fields") or []
            oc = r.get("output_contract") or {}
            if r.get("status") not in ("success", "partial", "failed"):
                issues.append("bad status %r" % r.get("status"))
            for f in fields:
                if f not in oc:
                    issues.append("field %s absent" % f)
                    continue
                v = oc[f]
                if isinstance(v, (dict, list)) and f in ("status", "case_id"):
                    issues.append("field %s is a %s" % (f, type(v).__name__))
                if v is None and f not in ("text",):
                    issues.append("field %s is null" % f)
            if "status" in oc and oc["status"] != r["status"]:
                issues.append("status mismatch: %r vs %r" % (oc["status"], r["status"]))
            if "case_id" in oc and oc["case_id"] != r["case_id"]:
                issues.append("case_id mismatch: %r vs %r" % (oc["case_id"], r["case_id"]))
            unresolved = r.get("contract_unresolved") or []
            if unresolved:
                issues.append("unresolved: " + ",".join(unresolved))
        flag = "OK  " if not issues else "FAIL"
        if issues:
            bad += 1
        print("%s %-24s status=%-8s fields=%s" % (
            flag, name, (r.get("status") if os.path.exists(rp) else "-"),
            ",".join(fields) if os.path.exists(rp) else "-"))
        for i in issues:
            print("     - " + i)
    print("%d skills, %d failed" % (len(SKILLS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
