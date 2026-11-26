#!/usr/bin/env python3
"""perf_bench.py -- wall time and memory of the shipped CLI, per paper.

Each run is a fresh `python outputs/scripts/parse_pdf.py <pdf> --out <tmp>`
subprocess with the CLI defaults (doc.json, text.md, report.json, tables/,
figures/, overlay/ all written), because that is the artefact the bundle
actually ships.  3 runs per paper, median reported.

Memory: Windows has no getrusage(RUSAGE_CHILDREN) equivalent, so the parent
samples the child's RSS with psutil every POLL_S seconds and reports the
maximum sample.  That is a *sampled max*, not the OS high-water mark; a short
spike between samples can be missed.  Method is recorded in the JSON note.

Page count and block count come from the shipped results/<name>/report.json
(identical stats to the fresh runs -- compare_tools.py asserts this).

Usage: python perf_bench.py [--corpus DIR] [--out FILE] [--runs 3]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import psutil

HERE = Path(__file__).resolve()
SCRIPTS = HERE.parent
BUNDLE = SCRIPTS.parent.parent
RESULTS = BUNDLE / "results"
WORK = Path("D:/dsh_workplace/work/_tools_probe")
CASES = ["resnet", "transformer", "bert", "gpt3", "vit"]
POLL_S = 0.025


def run_once(pdf, out_dir, timeout=900):
    if out_dir.exists():
        # this is our own scratch dir under work/, never inside bundle/
        for p in sorted(out_dir.glob("**/*"), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(SCRIPTS / "parse_pdf.py"), str(pdf),
           "--out", str(out_dir)]
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    peak = 0
    try:
        ps = psutil.Process(proc.pid)
        while proc.poll() is None:
            try:
                peak = max(peak, ps.memory_info().rss)
            except psutil.Error:
                pass
            time.sleep(POLL_S)
    finally:
        t = time.perf_counter() - t0
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("parse_pdf.py exit %d on %s" % (proc.returncode, pdf.name))
    return round(t, 3), round(peak / (1024.0 * 1024.0), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="D:/dsh_workplace/corpus")
    ap.add_argument("--out", default=str(RESULTS / "perf.json"))
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--cases", default=",".join(CASES))
    a = ap.parse_args()
    corpus = Path(a.corpus)
    WORK.mkdir(parents=True, exist_ok=True)

    cases = []
    for name in a.cases.split(","):
        pdf = corpus / ("%s.pdf" % name)
        report = json.loads((RESULTS / name / "report.json").read_text(encoding="utf-8"))
        pages = int(report["stats"]["n_pages_parsed"])
        blocks = int(report["stats"]["n_blocks"])
        secs, rss = [], []
        for i in range(a.runs):
            s, m = run_once(pdf, WORK / "perf" / ("%s_r%d" % (name, i)))
            secs.append(s)
            rss.append(m)
        med = round(statistics.median(secs), 3)
        cases.append({
            "file": pdf.name,
            "pages": pages,
            "seconds_median": med,
            "seconds_all": secs,
            "pages_per_s": round(pages / med, 2) if med else None,
            "peak_rss_mb": max(rss),
            "peak_rss_mb_all": rss,
            "blocks": blocks,
            "blocks_per_page": round(blocks / pages, 1) if pages else None,
        })
        print("[ok] %-18s pages=%3d med=%7.3fs rss=%6.1fMB"
              % (pdf.name, pages, med, max(rss)))

    tot_pages = sum(c["pages"] for c in cases)
    tot_secs = round(sum(c["seconds_median"] for c in cases), 3)
    res = {
        "schema": "pdf-struct/perf/1",
        "note": (
            "Wall time = one end-to-end CLI run (python outputs/scripts/"
            "parse_pdf.py <pdf> --out <scratch>) with default flags, so it "
            "includes page rasterisation of figures and the overlay PNGs that "
            "the shipped bundle writes; 3 runs per paper, median reported, "
            "runs discarded none. Peak RSS = sampled max: parent samples "
            "psutil.Process(child).memory_info().rss every %d ms (Windows has "
            "no RUSAGE_CHILDREN high-water mark), rounded up to the nearest "
            "sample; a spike shorter than the interval can be missed. pages and "
            "blocks are read from the shipped results/<name>/report.json, whose "
            "stats are identical to these runs. Environment: python %d.%d.%d, "
            "pymupdf %s, single process, warm file cache after the first run "
            "(each paper's 3 runs are consecutive)." % (
                int(POLL_S * 1000), sys.version_info[0], sys.version_info[1],
                sys.version_info[2], _fitz_ver())
        ),
        "cases": cases,
        "totals": {
            "files": len(cases),
            "pages": tot_pages,
            "seconds_median_sum": tot_secs,
            "pages_per_s": round(tot_pages / tot_secs, 2) if tot_secs else None,
            "peak_rss_mb_max": max(c["peak_rss_mb"] for c in cases),
            "blocks": sum(c["blocks"] for c in cases),
            "blocks_per_page": round(sum(c["blocks"] for c in cases) / tot_pages, 1)
            if tot_pages else None,
        },
    }
    out = Path(a.out)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    print("")
    print("%-18s %6s %10s %9s %9s %7s %6s" % (
        "file", "pages", "med_s", "pages/s", "rss_mb", "blocks", "b/page"))
    print("-" * 70)
    for c in cases:
        print("%-18s %6d %10.3f %9.2f %9.1f %7d %6.1f" % (
            c["file"], c["pages"], c["seconds_median"], c["pages_per_s"],
            c["peak_rss_mb"], c["blocks"], c["blocks_per_page"]))
    print("-" * 70)
    t = res["totals"]
    print("%-18s %6d %10.3f %9.2f %9.1f %7d %6.1f" % (
        "TOTAL", t["pages"], t["seconds_median_sum"], t["pages_per_s"],
        t["peak_rss_mb_max"], t["blocks"], t["blocks_per_page"]))
    print("")
    print("wrote %s" % out)
    return 0


def _fitz_ver():
    try:
        import pymupdf
        return pymupdf.VersionBind
    except Exception:  # noqa: BLE001
        return "?"


if __name__ == "__main__":
    sys.exit(main())
