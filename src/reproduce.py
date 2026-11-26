#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reproduce.py -- ARM entrypoint for the pdf-struct skill.

Runs the bundled parser over one or more PDFs and writes the same artifacts the
skill exposes to an agent: per-document report.json / text.md / tables/*.csv /
figures/*.png / overlay/*.png.

Usage:
    python src/reproduce.py --out results/run [--pdf a.pdf [--pdf b.pdf ...]]
    python src/reproduce.py --out results/run --self-check   # bundled smoke test

Exit codes mirror scripts/parse_pdf.py: 0 ok, 2 usage, 3 no text layer (OCR route), 4 selfcheck failed.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PARSER = os.path.join(ROOT, "outputs", "scripts", "parse_pdf.py")


def run_one(pdf, outdir):
    cmd = [sys.executable, PARSER, pdf, "--out", outdir]
    print("$ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd)
    return proc.returncode


def cli_self_check():
    """The bundled engine must import and the CLI must answer --help. Returns 0 or 4."""
    cmd = [sys.executable, PARSER, "--help"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0:
        print(out, flush=True)
        print("self-check: parse_pdf.py --help failed (exit %d)" % proc.returncode, flush=True)
        return 4
    try:
        import pymupdf  # noqa: F401
    except Exception as exc:  # pragma: no cover - only on a broken image
        print("self-check: pymupdf import failed: %s" % exc, flush=True)
        return 4
    print("self-check: engine import OK, CLI answers --help", flush=True)
    return 0


def report_self_check(outdir):
    """After a parse, every emitted report.json must carry a passing engine selfcheck."""
    import glob
    import json
    bad = []
    for path in sorted(glob.glob(os.path.join(outdir, "**", "report.json"), recursive=True)):
        try:
            with open(path, encoding="utf-8") as fh:
                rep = json.load(fh)
        except Exception as exc:
            bad.append((path, "unreadable report: %s" % exc))
            continue
        sc = rep.get("selfcheck") or {}
        if not sc.get("ok"):
            bad.append((path, "selfcheck not ok: %s" % (sc.get("errors") or sc)))
    if bad:
        for path, why in bad:
            print("self-check FAILED %s -- %s" % (path, why), flush=True)
        return 4
    print("self-check: all emitted report.json files report selfcheck ok", flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="parse PDFs into structured, source-traceable output")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--pdf", action="append", default=[], help="input PDF (repeatable)")
    ap.add_argument("--pages", default=None, help="page range forwarded to the parser, e.g. 1-6")
    ap.add_argument("--self-check", action="store_true",
                    help="verify the engine/CLI, and after parsing assert every report.json selfcheck is ok")
    args = ap.parse_args(argv)

    worst = 0
    if args.self_check:
        worst = max(worst, cli_self_check())

    if not args.pdf:
        if args.self_check:
            return worst
        print("no --pdf given; nothing to parse (see README.md for a worked example)", flush=True)
        return 2

    os.makedirs(args.out, exist_ok=True)
    for pdf in args.pdf:
        stem = os.path.splitext(os.path.basename(pdf))[0]
        tgt = os.path.join(args.out, stem)
        if args.pages:
            cmd = [sys.executable, PARSER, pdf, "--out", tgt, "--pages", args.pages]
            print("$ " + " ".join(cmd), flush=True)
            rc = subprocess.run(cmd).returncode
        else:
            rc = run_one(pdf, tgt)
        worst = max(worst, rc)
        print("case %s -> %s (exit %d)" % (stem, tgt, rc), flush=True)

    if args.self_check and worst == 0:
        worst = report_self_check(args.out)
    return worst


if __name__ == "__main__":
    sys.exit(main())
