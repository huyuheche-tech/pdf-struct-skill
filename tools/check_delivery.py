# -*- coding: utf-8 -*-
"""Verify the delivery layer on real runs of every skill.

Checks the three blocks that the rubric asks for are computed from the run,
not written by hand, and that a deliberately-bad case really turns a focus
question to satisfied=false.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SKILLS = [
    "reading-01-pdf", "reading-03-translation", "reading-10-notes",
    "reading-14-nanopub", "reading-15-kg", "writing-02-polish",
    "writing-04-references", "writing-08-intro", "writing-09-methods",
    "writing-13-latex",
]
FIELDS = ["delivery_manifest", "change_record", "requirement_coverage"]

checks = []


def add(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})


def run(skill, case_dir, out_dir, work_dir, contract=None):
    case_path = os.path.join(case_dir, "case.json")
    original = None
    if contract is not None:
        original = io.open(case_path, encoding="utf-8").read()
        data = json.loads(original)
        data["output_contract"] = contract
        with io.open(case_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    try:
        p = subprocess.run(
            [PY, os.path.join(ROOT, skill, "scripts", "run_case.py"),
             "--case", case_path, "--input-dir", case_dir,
             "--out", out_dir, "--work", work_dir],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180)
    finally:
        if original is not None:
            with io.open(case_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(original)
    rp = os.path.join(out_dir, "result.json")
    if not os.path.exists(rp):
        return p, None
    return p, json.load(io.open(rp, encoding="utf-8"))


def main():
    for skill in SKILLS:
        tmp = tempfile.mkdtemp(prefix="dlv-")
        saw_false = False
        case_names = sorted(n for n in os.listdir(
            os.path.join(ROOT, skill, "tests", "cases")) if n.startswith("case-"))
        for cname in case_names:
            cdir = os.path.join(ROOT, skill, "tests", "cases", cname)
            fixtures = os.path.join(ROOT, skill, "tests", "fixtures")
            # reading-01 keeps its PDFs in tests/fixtures while its case.json
            # names one of them; build a single input dir that has both.
            in_dir = os.path.join(tmp, skill + "-" + cname + "-in")
            if not os.path.isdir(in_dir):
                os.makedirs(in_dir)
            for f in os.listdir(cdir):
                sp = os.path.join(cdir, f)
                if os.path.isfile(sp):
                    shutil.copy2(sp, os.path.join(in_dir, f))
            if os.path.isdir(fixtures):
                for f in os.listdir(fixtures):
                    sp = os.path.join(fixtures, f)
                    if os.path.isfile(sp):
                        shutil.copy2(sp, os.path.join(in_dir, f))
            out = os.path.join(tmp, skill + "-" + cname + "-out")
            _p, r = run(skill, in_dir, out, os.path.join(tmp, "work"))
            tag = "%s/%s" % (skill, cname)
            if r is None:
                add(tag + ".result", False, "no result.json")
                continue
            add(tag + ".result", True)
            for f in FIELDS:
                add(tag + "." + f, r.get(f) is not None,
                    "null" if r.get(f) is None else "")
            dm = r.get("delivery_manifest") or {}
            files = dm.get("files") or []
            add(tag + ".manifest_files", bool(files), len(files))
            add(tag + ".manifest_real",
                all(os.path.isfile(os.path.join(out, f["name"])) for f in files),
                "a listed file is missing")
            add(tag + ".manifest_hash",
                all(len(f.get("sha256_16") or "") == 16 for f in files), "")
            cr = r.get("change_record") or {}
            add(tag + ".change_status", cr.get("status") == r.get("status"),
                "%s vs %s" % (cr.get("status"), r.get("status")))
            cov = r.get("requirement_coverage") or {}
            add(tag + ".coverage_4", len(cov) == 4, len(cov))
            add(tag + ".coverage_shape",
                all(isinstance(v.get("satisfied"), bool)
                    and isinstance(v.get("failed_checks"), list)
                    and v.get("guarantee") for v in cov.values()), "")
            if any(v.get("satisfied") is False for v in cov.values()):
                saw_false = True
        # every skill has a deliberately-bad case that must light up a verdict
        add(skill + "/bad_case_flags_a_question", saw_false, saw_false)

        # the three names must also be resolvable as output_contract slots
        cdir = os.path.join(ROOT, skill, "tests", "cases", "case-01")
        out = os.path.join(tmp, skill + "-contract")
        fixtures = os.path.join(ROOT, skill, "tests", "fixtures")
        tmpcase = os.path.join(out, "case.json")
        if not os.path.isdir(out):
            os.makedirs(out)
        src = json.load(io.open(os.path.join(cdir, "case.json"), encoding="utf-8"))
        for f in os.listdir(cdir):
            sp = os.path.join(cdir, f)
            if os.path.isfile(sp):
                shutil.copy2(sp, os.path.join(out, f))
        if os.path.isdir(fixtures):
            for f in os.listdir(fixtures):
                sp = os.path.join(fixtures, f)
                if os.path.isfile(sp):
                    shutil.copy2(sp, os.path.join(out, f))
        src["output_contract"] = FIELDS + ["status"]
        with io.open(tmpcase, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(src, ensure_ascii=False) + "\n")
        p = subprocess.run(
            [PY, os.path.join(ROOT, skill, "scripts", "run_case.py"),
             "--case", tmpcase, "--input-dir", out, "--out",
             os.path.join(out, "_o"), "--work", os.path.join(out, "_w")],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180)
        rp = os.path.join(out, "_o", "result.json")
        if os.path.exists(rp):
            rr = json.load(io.open(rp, encoding="utf-8"))
            add(skill + "/contract_slots",
                not rr.get("contract_unresolved")
                and all(rr["output_contract"].get(f) is not None for f in FIELDS),
                rr.get("contract_unresolved"))
        else:
            add(skill + "/contract_slots", False, "no result")
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [c for c in checks if not c["ok"]]
    report = os.path.join(ROOT, "results", "delivery-eval.json")
    if not os.path.isdir(os.path.dirname(report)):
        os.makedirs(os.path.dirname(report))
    with io.open(report, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"checks": checks, "failed": len(failed),
                             "note": "delivery-layer verification on real local runs"},
                            ensure_ascii=False, indent=1) + "\n")
    for c in failed:
        print("FAIL " + c["name"] + (" | " + c["detail"] if c["detail"] else ""))
    print("%d checks, %d failed" % (len(checks), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
