#!/usr/bin/env python3
"""Render the pages of a PDF and write a per-page transcription prompt.

Use this when `parse_pdf.py` exits 3 (the PDF has no text layer) or when a page
is reported as `empty`.  The skill does *not* bundle an OCR engine: a model with
vision reads `ocr/page-XX.png` and writes `ocr/page-XX.md`.  That is deliberate
-- guessing text from a blurry scan is worse than saying "unreadable".

Usage:
    python scripts/ocr_pages.py paper.pdf --out out/paper [--dpi 200] [--pages 1-6]
"""
from __future__ import annotations

import argparse
import json
import os

import pymupdf


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a) - 1, int(b)))
        elif part:
            out.append(int(part) - 1)
    return [i for i in out if 0 <= i < n]


PROMPT = """# 逐页转录任务（第 {pno} 页）

输入图片：`ocr/page-{pno:02d}.png`（{w}x{h}px，渲染自 PDF 第 {pno} 页）。

要求：

1. **逐行转录**页面上的所有可读文字，保持原始阅读顺序：先上后下、同一水平带内先左栏后右栏；
   不要按视觉位置做任何"重排"，也不要跨栏拼接。
2. **逐字保真**：保留连字（ﬁ/ﬂ）、希腊字母、上下标、破折号、引号样式；不要规范化数字或单位。
3. 页面顶/底的页眉页脚（期刊名、卷期、页码、arXiv 水印、版权行）单独放进
   `[header]` / `[footer]` 段，不要混进正文。
4. 表格按 Markdown 表格转录，保留空单元格；跨行列的合并单元格在表后用注释说明。
5. 图片区域用 `[[figure]]` 占位，并在其后写图注原文。
6. 公式用 `[[formula]]` 占位，右侧写你能确认的原文字符（不确定就不写）。
7. **无法辨认**的行写 `[unreadable]`，不要猜测、不要补全、不要用"大概是…"。
8. 输出纯文本，第一行固定为 `## page {pno}`，最后一行写 `confidence: high|medium|low`。

把结果保存为 `ocr/page-{pno:02d}.md`（旧流程的 `.txt` 仍被 merge_ocr.py 接受）。
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="render pages + write OCR prompts")
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--pages", default=None, help="e.g. 1-3,7")
    args = ap.parse_args(argv)

    ensure_dir(args.out)
    ocr_dir = os.path.join(args.out, "ocr")
    ensure_dir(ocr_dir)
    doc = pymupdf.open(args.pdf)
    todo = parse_pages(args.pages, doc.page_count)
    zoom = args.dpi / 72.0
    mat = pymupdf.Matrix(zoom, zoom)

    index = []
    for i in todo:
        page = doc[i]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        name = "page-%02d.png" % (i + 1)
        pix.save(os.path.join(ocr_dir, name))
        txt = os.path.join(ocr_dir, "page-%02d.txt" % (i + 1))
        index.append({"page": i + 1, "image": "ocr/" + name,
                      "transcript": "ocr/page-%02d.md" % (i + 1),
                      "transcript_exists": os.path.exists(txt) or os.path.exists(
                          os.path.join(ocr_dir, "page-%02d.md" % (i + 1))),
                      "text_layer_chars": len(page.get_text("text").strip())})
        with open(os.path.join(ocr_dir, "prompt-%02d.md" % (i + 1)), "w",
                  encoding="utf-8") as fh:
            fh.write(PROMPT.format(pno=i + 1, w=pix.width, h=pix.height))

    with open(os.path.join(ocr_dir, "prompt.md"), "w", encoding="utf-8") as fh:
        fh.write("# OCR 分支：逐页转录\n\n")
        fh.write("对下面每一页：读 `ocr/prompt-XX.md`，看 `ocr/page-XX.png`，"
                 "把转录写到 `ocr/page-XX.md`。全部写完后运行：\n\n")
        fh.write("```bash\npython scripts/merge_ocr.py %s\n```\n\n" % args.out)
        for it in index:
            fh.write("- 第 %d 页 -> `%s` -> `%s`（已有转录：%s）\n"
                     % (it["page"], it["image"], it["transcript"],
                        "是" if it["transcript_exists"] else "否"))
    with open(os.path.join(ocr_dir, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"pdf": os.path.basename(args.pdf), "dpi": args.dpi,
                   "pages": index}, fh, ensure_ascii=False, indent=2)
    print("rendered %d page(s) to %s" % (len(index), ocr_dir))
    print("next: transcribe with a vision model, then run scripts/merge_ocr.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())