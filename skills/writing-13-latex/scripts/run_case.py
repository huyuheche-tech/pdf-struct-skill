#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry for the LaTeX build doctor.

    # phase 1 -- static analysis, safe repairs, optional build
    python scripts/run_case.py --case /input/case.json --input-dir /input \
        --out /app/output --work /app/work --fix

    # phase 2 -- validate a model-repaired .tex and emit the deliverables
    python scripts/run_case.py --case /input/case.json --input-dir /input \
        --out /app/output --work /app/work --draft /app/work/draft.tex --fix --compile

Without --draft the script still writes every artifact, but status is
"partial" and next_step says which file the model must produce: a deterministic
script must not pretend a human repair happened.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skillkit as sk          # noqa: E402
import tex_doctor as td        # noqa: E402


def safe(s):
    """stdout must stay ASCII; Chinese goes into files, not the console."""
    return str(s).encode("ascii", "replace").decode("ascii")


def pick_main(case, materials, want=None):
    if want and os.path.isfile(want):
        return os.path.abspath(want)
    if isinstance(case, dict):
        for k in ("main_tex", "main", "tex", "source", "manuscript"):
            v = case.get(k)
            if isinstance(v, str) and v.lower().endswith(".tex"):
                for cand in (v, os.path.join(os.path.dirname(want or ""), v)):
                    if os.path.isfile(cand):
                        return os.path.abspath(cand)
    tex = [m for m in materials if m["name"].lower().endswith(".tex")
           and not os.path.basename(m["path"]).lower().startswith(("fixed", "draft"))]
    if not tex:
        return None
    return max(tex, key=lambda m: len(m["text"]))["path"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default=None)
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--draft", default=None, help="model-repaired .tex")
    ap.add_argument("--main", default=None, help="explicit main .tex")
    ap.add_argument("--fix", action="store_true", help="apply safe repairs -> fixed.tex")
    ap.add_argument("--compile", dest="compile", action="store_true", default=None)
    ap.add_argument("--no-compile", dest="compile", action="store_false")
    a = ap.parse_args(argv)

    case_path = a.case or os.path.join(a.input_dir, "case.json")
    case, case_path = sk.load_case(case_path)
    input_dir = a.input_dir if os.path.isdir(a.input_dir) else (os.path.dirname(case_path) or ".")
    for d in (a.out, a.work):
        if not os.path.isdir(d):
            os.makedirs(d)

    materials = sk.material_texts(case, case_path, input_dir)
    tex_path = pick_main(case, materials, a.main)
    bibs = {m["name"]: m["text"] for m in materials if m["kind"] == "bib"}
    tex_name = os.path.basename(tex_path) if tex_path else "main.tex"

    do_compile = a.compile
    if do_compile is None:
        do_compile = not (isinstance(case, dict) and case.get("compile") is False)

    # ---- no material: fail honestly -------------------------------------
    if not tex_path:
        sk.jdump(os.path.join(a.out, "checks.json"),
                 {"errors": [{"code": "no_material"}], "warnings": [],
                  "summary": {"n_errors": 1, "n_warnings": 0}})
        sk.write_report(a.out, "LaTeX / no material",
                        ["- status: **failed**", "- 输入目录里没有可读的 .tex 主文件。"])
        result = sk.write_result(
            a.out, "latex-build-doctor", "LaTeX 写作与编译", case, "failed",
            {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
             "latex": "", "diagnostics": {"errors": [], "warnings": []},
             "checks": {"errors": [{"code": "no_material"}], "warnings": []},
             "metrics": {"errors": 0, "warnings": 0, "compiled": False,
                         "cite_keys": 0, "labels": 0},
             "files": {}},
            uncertainty={"warnings": [{"code": "no_material"}], "missing_fields": [],
                         "next_step": "把主 .tex 与 .bib 放进 /input 后重跑"},
            sources=sk.sources_of([m["path"] for m in materials]))
        print("case_id=%s status=failed reason=no_tex" % safe(result["case_id"]))
        return 1

    src_text = sk.read_text(tex_path)
    draft_path = a.draft
    if draft_path and os.path.isfile(draft_path):
        src_text = sk.read_text(draft_path)
    has_draft = bool(draft_path and os.path.isfile(draft_path))

    pre = td.analyze(src_text, tex_name, bibs)
    pre_counts = {"errors": len(pre["errors"]), "warnings": len(pre["warnings"])}

    text = src_text
    fixes = []
    if a.fix:
        undef = {d["key"] for d in pre["errors"]
                 if d["code"] == "cite_undefined" and d.get("key")}
        new_lines, fixes = td.apply_fixes(pre["lines"], tex_name, undef)
        text = "\n".join(new_lines)
        with open(os.path.join(a.out, "fixed.tex"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    post = td.analyze(text, tex_name, bibs)
    errors, warnings = post["errors"], post["warnings"]
    metrics = {"errors": len(errors), "warnings": len(warnings), "compiled": False,
               "cite_keys": len(post["stats"]["cite_keys"]),
               "labels": post["stats"]["n_labels"],
               "lines": post["stats"]["lines"]}

    compile_info = {"available": None, "skipped": True, "compiled": False,
                    "compiler_missing": td.find_engine()[0] is None,
                    "errors": [], "note": "--compile not requested"}
    if do_compile and not errors:
        compile_info = td.compile_tex(text, tex_name, bibs, a.work)
        for e in compile_info.get("errors", []):
            errors.append(td.diag("compile_error", "error", e["file"] or tex_name,
                                  e.get("line") or 0, "",
                                  "编译错误：%s" % e["message"]))
        metrics["compiled"] = bool(compile_info.get("compiled"))
        if compile_info.get("compiler_missing"):
            warnings.append(td.diag("compiler_missing", "warning", tex_name, 0, "",
                                    "本机没有 pdflatex/latexmk，只做了静态检查；"
                                    "不得声称编译成功"))
        metrics["errors"] = len(errors)
    elif do_compile and errors:
        compile_info["note"] = "skipped: static errors remain"

    if not has_draft:
        status = "partial"
    elif errors:
        status = "partial"
    else:
        status = "success"

    patches = td.patch_plan(errors + warnings)
    report = td.render_report(sk.case_id_of(case, [tex_path]), tex_name, errors, warnings,
                              fixes, patches, metrics, compile_info, pre_counts)
    with open(os.path.join(a.out, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(report)

    diagnostics = {"errors": errors, "warnings": warnings, "fixes": fixes,
                   "patch_plan": patches, "compile": compile_info,
                   "pre_fix": pre_counts}
    sk.jdump(os.path.join(a.out, "diagnostics.json"), diagnostics)
    summary = {"n_errors": len(errors), "n_warnings": len(warnings),
               "compiled": metrics["compiled"],
               "compiler_missing": bool(compile_info.get("compiler_missing")),
               "lines": metrics["lines"], "pre_fix": pre_counts}
    sk.jdump(os.path.join(a.out, "checks.json"),
             {"errors": errors, "warnings": warnings, "fixes": fixes,
              "patch_plan": patches, "compile": compile_info, "summary": summary})

    main_result = {
        "case_id": sk.case_id_of(case, [tex_path]),
        "latex": text,
        "diagnostics": {"errors": errors, "warnings": warnings, "fixes": fixes,
                        "patch_plan": patches, "compile": compile_info},
        "checks": {"errors": errors, "warnings": warnings, "summary": summary},
        "metrics": metrics,
        "files": {"report": "report.md", "diagnostics": "diagnostics.json",
                  "checks": "checks.json",
                  **({"fixed_tex": "fixed.tex"} if a.fix else {})},
    }
    uncertainty = {
        "warnings": warnings,
        "human_review": [w for w in warnings if w["code"] in
                         ("caption_missing", "table_no_rules", "bib_unused",
                          "package_duplicate", "cite_todo", "compiler_missing")],
        "missing_fields": [],
        "note": ("static checks are deterministic; compiled is true only after a real "
                 "two-pass build. Unescaped-special detection is a high-confidence "
                 "heuristic, not a TeX parser."),
        "compiled": metrics["compiled"],
        "compiler_missing": bool(compile_info.get("compiler_missing")),
    }
    if not has_draft:
        uncertainty["next_step"] = ("save the repaired source as /app/work/draft.tex "
                                    "(or accept fixed.tex) and rerun with "
                                    "--draft /app/work/draft.tex --fix --compile")
    elif errors:
        uncertainty["next_step"] = ("fix the %d remaining errors listed in "
                                    "diagnostics.json, then rerun" % len(errors))

    result = sk.write_result(
        a.out, "latex-build-doctor", "LaTeX 写作与编译", case, status, main_result,
        evidence={"anchors": [{"file": d["file"], "line": d["line"], "code": d["code"]}
                              for d in (errors + warnings)[:40]],
                  "method": "delimiter/env/math balance, cite<->bib, ref<->label, "
                            "tabular column count, optional two-pass build"},
        uncertainty=uncertainty,
        sources=sk.sources_of([tex_path] + [m["path"] for m in materials
                                            if m["kind"] == "bib"]),
        runs=[{"step": "tex_doctor", "status": status, "errors": len(errors),
               "warnings": len(warnings), "compiled": metrics["compiled"],
               "fixes": len(fixes)}])

    print("case_id=%s status=%s errors=%d warnings=%d compiled=%s fixes=%d"
          % (safe(result["case_id"]), result["status"], len(errors), len(warnings),
             metrics["compiled"], len(fixes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
