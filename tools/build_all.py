# -*- coding: utf-8 -*-
"""Build all ten skill bundles with the shared packer."""
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
GH = "https://github.com/huyuheche-tech/pdf-struct-skill"
SKILLS = [
    ("reading-01-pdf", "product-arena-08-3027d350", "阅读01｜文献文档解析", GH),
    ("reading-03-translation", "product-arena-01-5a9928c1", "阅读03｜文献翻译",
     GH + "/tree/main/skills/reading-03-translation"),
    ("reading-10-notes", "product-arena-06-6d8cf72b", "阅读10｜文献总结与结构化笔记",
     GH + "/tree/main/skills/reading-10-notes"),
    ("reading-14-nanopub", "product-arena-09-0e8befd4", "阅读14｜Nanopublication",
     GH + "/tree/main/skills/reading-14-nanopub"),
    ("reading-15-kg", "product-arena-10-760d1a0b", "阅读15｜文献知识图谱构建",
     GH + "/tree/main/skills/reading-15-kg"),
    ("writing-02-polish", "product-arena-02-7051d92d", "写作02｜学术语言润色", ""),
    ("writing-04-references", "product-arena-03-429cc14d", "写作04｜参考文献与引用管理", ""),
    ("writing-08-intro", "product-arena-04-4b82ad21", "写作08｜引言与相关工作写作", ""),
    ("writing-09-methods", "product-arena-05-64faa4a2", "写作09｜方法与实验章节写作", ""),
    ("writing-13-latex", "product-arena-07-865de7e4", "写作13｜LaTeX 写作与编译", ""),
]


def clean(path):
    if not os.path.isdir(path):
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            os.remove(os.path.join(root, f))
        for d in dirs:
            os.rmdir(os.path.join(root, d))
    os.rmdir(path)


def main():
    only = sys.argv[1:] or [s[0] for s in SKILLS]
    built, failed = [], []
    for name, cid, title, gh in SKILLS:
        if name not in only:
            continue
        out = os.path.join(HERE, "build", name)
        clean(out)
        cmd = [PY, os.path.join(HERE, "pack_skill.py"), "--skill",
               os.path.join(HERE, name), "--out", out, "--challenge", cid,
               "--title", title]
        if gh:
            cmd += ["--github-url", gh]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
        tail = (p.stdout or "").strip().splitlines()[-2:]
        print(("OK   " if p.returncode == 0 else "FAIL ") + name + " | " + " / ".join(tail))
        if p.returncode == 0:
            built.append((name, cid, title, out))
        else:
            failed.append((name, p.stdout + p.stderr))
    lines = ["# Build index", "", "| skill | challenge | bundle |", "|---|---|---|"]
    for name, cid, title, out in built:
        lines.append("| %s | %s | build/%s |" % (name, cid, name))
    io.open(os.path.join(HERE, "build", "INDEX.md"), "w", encoding="utf-8",
            newline="\n").write("\n".join(lines) + "\n")
    print("%d built, %d failed" % (len(built), len(failed)))
    for name, log in failed:
        print("---- " + name)
        print(log[-1200:])
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
