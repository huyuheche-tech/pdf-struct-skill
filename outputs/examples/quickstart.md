# Quickstart —— 粘贴即用（给 Agent 的最短路径）

> 30 行版本。完整契约见 `../SKILL.md`，字段含义见 `../references/schema.md`。
> 目标：**一次粘贴 → 拿到带页码与坐标的结构化结果**，不读长文档也能正确调用。

## 1. 安装（一次）

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pymupdf pillow
```

## 2. 三行命令

```bash
python scripts/parse_pdf.py paper.pdf --out out/paper --no-overlay --pages 1-2   # 探版：先看 2 页
python scripts/parse_pdf.py paper.pdf --out out/paper                            # 全量
python scripts/baseline_compare.py paper.pdf --doc out/paper/doc.json            # 可选：量化"比裸 dump 好在哪"
```

退出码：`0` 成功 / `2` 用法或文件问题 / `3` 无文本层（转 `ocr_pages.py` + `merge_ocr.py`）/ `4` 自检未过。

## 3. 读什么（按优先级）

| 想回答 | 读这个 | 关键字段 |
|---|---|---|
| 章节结构 | `out/paper/doc.json` | `sections[].path/level/page/bbox` |
| 某段原文 | `out/paper/text.md`（每块前有 `<!-- p3-b004 \| type=body \| bbox=… -->`） | — |
| 表格 | `out/paper/tables/T*.csv` + `doc.json.tables[]` | `cells`（二维文本）、`bbox_cells`（逐格坐标） |
| 图与图注 | `doc.json.figures[]` | `caption`、`bbox`、`artwork`（raster/vector） |
| 可信度 | `out/paper/report.json` | `selfcheck.ok`、`stats.char_recall`、`warnings[]` |

## 4. 交回给用户时必须带上的三件事

1. `selfcheck.ok == true`（否则先修，别交付）；
2. `stats.char_recall`（有文本层时应在 `0.95–1.05`；OCR 路径为 `null`，不许编造）；
3. 所有被标注的不确定项：`pages[].empty`、`tables_rejected`、`n_unassigned > 0`、`warnings[]`。

## 5. 三条纪律

- **不猜**：`[unreadable]` / `bbox: null` 比编造坐标好；OCR 块永远标 `bbox_source: "vision"`。
- **不合并**：多份 PDF 各自一个输出目录，不要拼 `doc.json`。
- **不复述**：回答"第 3 节讲了什么"时，用 `sections[].path` 定位，不要凭记忆改写原文。

> 反面教材（裸 dump 的典型产物）：两栏交错、页眉页脚进正文、表格单元格串成 `3 3××3 6 64`、图注当正文、块无坐标无法回查。
> 量化对照见 `../references/baseline.md`（同一批语料，同一套判据）。
