# 最小调用示例（示例，非正式评测结果）

> 本目录下所有内容都是**调用演示**，用于说明"怎么调用、会得到什么形状的输出"，
> 不是本次挑战的正式测试结果，也不代表隐藏用例的得分。示例语料是两篇公开 arXiv 预印本。
> 只想要最短路径：看 `quickstart.md`（30 行，粘贴即用）；想知道"比裸 dump 好在哪"：看 `../references/baseline.md`。

## 示例 1：一篇有文本层的双栏论文（最短路径）

```bash
python scripts/parse_pdf.py corpus/resnet.pdf --out out/resnet
```

打印（真实输出，见 `results/run.log`）：

```
parsed: resnet.pdf
pages=12 blocks=583 headings=17 formulas=7 tables=14 figures=7
text_layer_chars=49574 emitted_chars=47956 char_recall=1.0018
selfcheck: OK (0 errors, 0 warnings)
```

得到：

```
out/resnet/doc.json          结构化结果（唯一权威产物）
out/resnet/text.md           阅读顺序文本，每块带 <!-- p4-b021 | type=body | col=1 | bbox=... --> 溯源注释
out/resnet/report.json       精简报告（输入指纹、逐页栏数、统计、自检）
out/resnet/tables/T1.csv     表格 CSV（本例 T1 = ResNet 结构表，7 列 × 多行嵌套单元格）
out/resnet/figures/F1..F7.png 图区裁剪
out/resnet/overlay/page-01.png 判版可视化（可用于人工复核栏线与阅读顺序）
```

本目录只附少量节选以便直接查看：`text-resnet.excerpt.md`（前 46 行）、`table-resnet-T1.csv`。
完整的 `report.json` / `text.md` 见 `results/resnet/`、`results/transformer/`（同一次运行的真实产物）。

## 示例 2：只看某几页（适合先探版面再全量）

```bash
python scripts/parse_pdf.py corpus/transformer.pdf --out out/probe --pages 1-2 --no-overlay
```

先看 `out/probe/report.json` 里 `pages[].columns` 与 `gutters` 是否符合肉眼判断，再决定是否全量跑。
建议所有正式解析都先跑 2 页探版——这一步能提前发现"栏数判错"与"扫描件"两类致命问题。

## 示例 3：扫描件（无文本层）走视觉转录分支

```bash
python scripts/parse_pdf.py scan.pdf --out out/scan          # 退出码 3，提示无文本层
python scripts/ocr_pages.py scan.pdf --out out/scan --dpi 200
# 用视觉模型逐页转录 out/scan/ocr/prompt-01.md 指定的图片，写到 out/scan/ocr/page-01.md
python scripts/merge_ocr.py out/scan --require all           # 合并进 doc.json
```

合并后的块带 `source: "vision"`、`bbox: null`、`confidence: high|medium|low`——
**能定位到页，不能定位到框，这一点必须如实写进结果**，不能编造坐标。

## 示例 4：被 Agent 调用时的一次完整往返

输入（Agent 侧）：

```json
{"case_id": "demo-resnet", "input": "corpus/resnet.pdf",
 "asks": ["章节树", "第 3 节的表格", "图 3 的图注原文"]}
```

Skill 侧动作：`parse_pdf.py` → 读 `doc.json` → 取 `sections` / `tables[].rows` / `figures[]`。
返回（节选）：

```json
{
  "case_id": "demo-resnet",
  "status": "success",
  "result": {
    "sections": [{"path": "3. Deep Residual Learning", "level": 1, "page": 3, "block_id": "p3-b001"},
                 {"path": "3. Deep Residual Learning / 3.1. Residual Learning", "level": 2, "page": 3}],
    "figure_caption": {"id": "F2", "page": 2,
                       "text": "Figure 2. Residual learning: a building block."}
  },
  "evidence": [{"block_id": "p2-b009", "page": 2, "bbox": [86.62, 146.19, 249.86, 167.12]},
               {"block_id": "p3-b001", "page": 3, "bbox": [50.11, 108.96, 185.43, 120.92]}],
  "uncertainty": []
}
```

`evidence` 里每一项都能在 `doc.json` 中用 `id` 反查，这是"核得回"的落地形式。

## 示例 5：量化"比裸 Agent 好多少"

```bash
python scripts/parse_pdf.py corpus/resnet.pdf --out out/resnet
python scripts/baseline_compare.py corpus/resnet.pdf --doc out/resnet/doc.json
```

输出（真实数字，见 `../references/baseline.md` 与 `results/baseline.json`）：

```
baseline vs skill: resnet.pdf (12 pages)
  blocks with page+bbox        0              583
  sections                     0              16
  tables / cells               0 / 0          14 / 213
  figure-label chars in body   1653           0
  cross-column interleavings   32             0
```

左边是 `page.get_text("text")`（Agent 最默认的写法），右边是本引擎。判据全部由 PDF 几何独立计算，换实现只需替换 `doc.json`。

> 具体数字（可直接对照 `results/*/report.json`）：transformer 510 块 / 26 标题 / `char_recall` 1.0012；resnet 583 块 / 17 标题 / 1.0018。
