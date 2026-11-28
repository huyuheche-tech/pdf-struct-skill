# -*- coding: utf-8 -*-
"""Validate every built bundle against the worker's known prechecks."""
import datetime as dt
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
SKILLS = ["reading-01-pdf", "reading-03-translation", "reading-10-notes",
          "reading-14-nanopub", "reading-15-kg", "writing-02-polish",
          "writing-04-references", "writing-08-intro", "writing-09-methods",
          "writing-13-latex"]
GH = {"reading-01-pdf", "reading-03-translation", "reading-10-notes",
      "reading-14-nanopub", "reading-15-kg"}
TYPES = {"figure", "table", "metric", "array", "data", "log", "checkpoint", "scalar"}
FORMATS = {"png", "jpg", "pdf", "svg", "csv", "tsv", "json", "npy", "npz",
           "h5", "parquet", "txt", "other"}
STEP_TYPES = {"thought", "tool_call", "tool_result", "artifact", "reflection",
              "observation", "decision"}


def jload(p):
    return json.load(io.open(p, encoding="utf-8-sig"))


def count_files(p):
    n = 0
    for _r, _d, fs in os.walk(p):
        n += len(fs)
    return n


def check(name):
    d = os.path.join(BUILD, name)
    issues, warns = [], []
    need = ["arm_manifest.json", "README.md", "src/reproduce.py",
            "execution/run.log", "execution/results", "characterization.json",
            "trace/trace.jsonl", "outputs/SKILL.md"]
    for x in need:
        if not os.path.exists(os.path.join(d, x)):
            issues.append("missing " + x)
    if not os.path.exists(os.path.join(d, "outputs", "environment", "resources.yaml")):
        issues.append("missing outputs/environment/resources.yaml")
    n_res = count_files(os.path.join(d, "results")) if os.path.isdir(os.path.join(d, "results")) else 0
    if n_res > 50:
        issues.append("results/ %d files >50" % n_res)
    native = os.path.join(d, "native_trace")
    n_native = count_files(native) if os.path.isdir(native) else 0
    if n_native != 1:
        issues.append("native_trace %d files != 1" % n_native)
    if (name in GH) != os.path.exists(os.path.join(d, "GITHUB_URL.txt")):
        issues.append("GITHUB_URL.txt presence wrong for this challenge")
    if name in GH:
        first = io.open(os.path.join(d, "GITHUB_URL.txt"), encoding="utf-8").read().splitlines()[0]
        if not first.startswith("https://github.com/"):
            issues.append("GITHUB_URL first line is not a github URL")
    try:
        man = jload(os.path.join(d, "arm_manifest.json"))
    except Exception as exc:
        return ["manifest unreadable: %s" % exc], warns, {}
    if man.get("arm_version") not in ("1.0", "1.1"):
        issues.append("bad arm_version")
    if not man.get("paper", {}).get("title"):
        issues.append("no paper.title")
    entry = man.get("entrypoint")
    if entry and not os.path.exists(os.path.join(d, entry)):
        issues.append("entrypoint missing")
    ex = man.get("execution", {})
    if ex.get("exit_code") != 0:
        issues.append("execution.exit_code=%r" % ex.get("exit_code"))
    arts = ex.get("artifacts") or []
    ids = set()
    for a in arts:
        ids.add(a.get("id"))
        if a.get("type") not in TYPES:
            issues.append("artifact %s bad type %r" % (a.get("id"), a.get("type")))
        if a.get("format") not in FORMATS:
            issues.append("artifact %s bad format %r" % (a.get("id"), a.get("format")))
        if not os.path.exists(os.path.join(d, a.get("path", ""))):
            issues.append("artifact %s missing file %s" % (a.get("id"), a.get("path")))
    for e in man.get("expected_outputs") or []:
        for pid in e.get("produced_by") or []:
            if pid not in ids:
                issues.append("expected_output %s -> unknown %s" % (e.get("name"), pid))
    h = man.get("handoff") or {}
    if h.get("status") not in ("complete", "stuck", "partial", "failed"):
        issues.append("bad handoff.status")
    # trace
    steps = []
    for line in io.open(os.path.join(d, "trace", "trace.jsonl"), encoding="utf-8"):
        if line.strip():
            steps.append(json.loads(line))
    if len(steps) < 6:
        issues.append("trace has %d steps" % len(steps))
    try:
        ran = dt.datetime.fromisoformat(ex.get("ran_at"))
        wall = float(ex.get("wall_time_s") or 0)
        lo, hi = ran - dt.timedelta(seconds=max(2 * wall, 600)), ran + dt.timedelta(seconds=max(2 * wall, 600))
        for s in steps:
            if s.get("step_type") not in STEP_TYPES:
                issues.append("bad step_type %r" % s.get("step_type"))
            ts = s.get("timestamp")
            if ts:
                t = dt.datetime.fromisoformat(ts)
                if not (lo <= t <= hi):
                    issues.append("trace timestamp outside window: " + ts)
    except Exception as exc:
        warns.append("trace time check skipped: %s" % exc)
    call_ids = {s.get("tool_call_id") for s in steps if s.get("step_type") == "tool_call"}
    res_ids = {s.get("tool_call_id") for s in steps if s.get("step_type") == "tool_result"}
    if not call_ids or call_ids != res_ids:
        warns.append("tool_call/result ids do not pair")
    cost = sum(float(s.get("cost_usd") or 0) for s in steps)
    if cost < 0.01:
        warns.append("trace cost %.3f < 0.01" % cost)
    # run.log
    log = io.open(os.path.join(d, "execution", "run.log"), encoding="utf-8",
                  errors="replace").read()
    if "exit_code: 0" not in log:
        issues.append("run.log does not record exit_code: 0")
    # summary
    try:
        summ = jload(os.path.join(d, "execution", "results", "summary.json"))
        if len(summ.get("cases", [])) != 3:
            issues.append("summary has %d cases" % len(summ.get("cases", [])))
        for c in summ["cases"]:
            rp = os.path.join(d, "execution", "results", c["case"], "result.json")
            if not os.path.exists(rp):
                issues.append("no result for " + c["case"])
                continue
            r = jload(rp)
            if r.get("case_id") != c["case_id"]:
                issues.append("case_id mismatch " + c["case"])
            if r.get("status") == "failed":
                issues.append("case %s failed" % c["case"])
    except Exception as exc:
        issues.append("summary unreadable: %s" % exc)
    # every path advertised in resources.yaml must exist inside outputs/;
    # a dead path there is read as "the skill depends on a file it does not ship"
    res_yaml = os.path.join(d, "outputs", "environment", "resources.yaml")
    if os.path.exists(res_yaml):
        import re as _re
        txt = io.open(res_yaml, encoding="utf-8").read()
        for rel in _re.findall(r"-[ ]*path:[ ]*([^ \n\r]+)", txt):
            if not os.path.exists(os.path.join(d, "outputs", rel)):
                issues.append("resources.yaml lists a missing path: " + rel)
    else:
        issues.append("outputs/environment/resources.yaml missing")
    # the platform preflight rejects unsupported Skill resources.  It says so in
    # plain text ("unsupported Skill resource: train.log"), but only after the
    # attempt is created, so catch it here instead.
    allowed = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".csv", ".bib",
               ".tex", ".ris", ".pdf", ".png", ".jpg", ".jpeg", ".svg"}
    for sub in ("outputs", "results"):
        root = os.path.join(d, sub)
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                ext = os.path.splitext(f)[1].lower()
                if ext not in allowed:
                    rel = os.path.relpath(os.path.join(dp, f), d).replace(os.sep, "/")
                    issues.append("unsupported resource type: " + rel)
    return issues, warns, {"results": n_res, "steps": len(steps), "cost": round(cost, 3)}


def main():
    bad = 0
    for name in SKILLS:
        issues, warns, info = check(name)
        flag = "OK  " if not issues else "FAIL"
        if issues:
            bad += 1
        print("%s %-24s results=%-3s steps=%-2s cost=%-5s" % (
            flag, name, info.get("results"), info.get("steps"), info.get("cost")))
        for i in issues:
            print("     - " + i)
        for w in warns:
            print("     ~ " + w)
    print("%d bundles, %d failed" % (len(SKILLS), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
