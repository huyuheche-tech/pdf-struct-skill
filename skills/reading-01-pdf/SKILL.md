---
name: weekly-skill
description: 解析科研 PDF（arXiv/CVPR/期刊/中文论文/扫描件），产出带 page+bbox 溯源的层级结构、阅读顺序正确的正文、按行列单元格拆分的表格、公式与图注，并附带逐块可核验的质量报告。当任务涉及"读论文/提取 PDF 内容/表格转 CSV/多栏排版还原/扫描件 OCR 转录"时使用。
---

# 科研 PDF 结构化解析（pdf-struct）

## 0. 运行契约（平台执行时先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，把案例放在 `/input/case.json` + `task.md`，要求把成品写到
`/app/output/`。**一条命令就能满足这个契约**：

```bash
python scripts/run_case.py          # 默认读 /input/case.json，写 /app/output/result.json
```

它做三件事：从 `case.json`（递归找 `*.pdf`，找不到就扫 `/input`）定位 PDF → 调 `scripts/parse_pdf.py`
解析 → 写 `result.json` 和每个 PDF 的 `doc.json`、`text.md`。本地调试用
`--case <case.json> --input-dir <dir> --out <dir> --work <dir>`。

`result.json` 固定字段：

| 字段 | 含义 |
|---|---|
| `case_id` | 取自 `case.json` 的 `case_id`/`id`，缺省用 PDF 文件名 |
| `status` | `success` / `partial` / `failed`（有 warning 或自检未过就是 `partial`） |
| `main_result.documents[]` | 每个 PDF 的 `pages/title/sections/tables/figures/formulas/references/char_recall` |
| `evidence` | 溯源方式（page+bbox）与各 PDF 的 `doc_json` |
| `uncertainty` | `warnings`、`missing_fields`、不可读页；**读不出就写这里，不许猜** |
| `sources` | 输入文件、sha256、字节数 |
| `output_contract` | 按 `case.json` 的 `output_contract` 逐字段回填；不认识的字段写 `null` 并记入 `missing_fields` |
| `runs` | 每次解析的退出码与 stderr 尾部 |

**预算**：单案例 ≤900 秒、≤64 次模型请求、单次回复 ≤16384 token。默认 `--no-overlay`（不出调试图），
100 页以内通常 1–2 分钟；超过 200 页先按 `--pages` 分批，避免超时。
**资源限制**：≤50 个 UTF-8 文本文件、单文件 ≤500KB、合计 ≤2MB、无符号链接。

**扫描件**：`run_case.py` 发现 `parse_pdf.py` 退出码 3 时，会把 `no_text_layer` 写入 `uncertainty`，
并给出下一步（`ocr_pages.py` → 逐页 `ocr/page-XX.md` → `merge_ocr.py --require all`）。
此时**不要**把空文本当成功，`status` 必须是 `partial`。

**边界**：不解释公式语义、不判断科学结论真假、不做翻译；只负责把版面和文字正确搬出来并留下溯源。

## 1. 用途

把一个 PDF 变成**可被程序继续消费、并且每一块都能回到原页坐标**的结构：

- `doc.json`：机器接口（schema `pdf-struct/2`），块级 `page` + `bbox` + `type` + `order`；
- `text.md`：人类/LLM 读版，每块前有 `<!-- p3-b004 | type=body | col=0 | bbox=… -->` 溯源注释；
- `tables/T*.csv`：表格按行/列/单元格拆开；
- `figures/F*.png`：图区裁切（含矢量图，不依赖位图嵌入）；
- `overlay/page-XX.png`：把分栏线、块的类型与阅读序号画回页面，用于肉眼验版；
- `report.json`：统计与自检结果（字符召回、块数、逐页栏数）。

**适用条件**：有文本层的电子版论文（PDF 1.4+，任何语言）；扫描件走 §6 的 OCR 分支。
**不适用**：需要理解公式语义、需要复现实验、需要读 PDF 里的嵌入附件（这些属于下游任务，本 Skill 只负责"把版面和文字正确搬出来"）。

## 2. 调用方式

```bash
# 依赖：python 3.10+，pymupdf（2.1 实测），pillow（仅 overlay/裁图需要）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pymupdf pillow

python scripts/parse_pdf.py paper.pdf --out out/paper
```

常用参数：

| 参数 | 作用 |
|---|---|
| `--pages 1-6` | 只解析部分页（快速试跑、大文件取样） |
| `--no-overlay` | 跳过 overlay 渲染（只出 doc.json/text.md/tables/figures；本包未单独计时，默认路径 140 页 132.6 s） |
| `--no-figures` | 不裁图 |
| `--no-text-md` | 只要 doc.json |
| `--dpi 110` | overlay 渲染分辨率（默认 110） |

退出码即结论：`0` 成功；`2` 用法错误；`3` **该 PDF 无文本层，必须转 OCR 分支**；`4` 自检不通过（看 `report.json` 的 `selfcheck.errors`）。

## 2.1 题面四问对齐（评审核对用）

| 题面关注 | 本 Skill 的确定性保证 | 失败信号 | 不覆盖 |
|---|---|---|---|
| 提得全 | 逐字提取 + `char_recall` + 页眉页脚计数 | `char_recall<0.9`（exit 4） | 图片内文字（单独标 `figure_label`） |
| 排得对 | 栏投票 + 带区排序 + 跨栏判据 | 自检 `cross_gutter` | 极端三/四栏 |
| 拆得清 | 章节树 + `find_tables` + words 重建单元格 | `sparse_table` warning | 无框线表 |
| 核得回 | 每块 page+bbox；OCR 路径 `bbox:null` 明示 | 自检 `no_bbox` | 扫描件识别率 |

## 3. 输入

| 输入 | 说明 |
|---|---|
| `paper.pdf` | 单个 PDF。多文件时逐个跑，各自独立输出目录（不要合并 doc.json）。 |
| 可选 `--pages` | 指定页范围后，`report.json` 的 `input.pages` 与 `stats.n_pages_parsed` 会如实记录只跑了一部分。 |

## 4. 输出契约

### 4.1 `doc.json`（稳定字段）

```jsonc
{
  "schema": "pdf-struct/2",
  "source":  {"path", "sha256", "bytes", "pages"},
  "engine":  {"name": "pymupdf", "version", "mupdf", "python", "pipeline"},
  "document":{"pages", "column_template", "has_text_layer"},
  "pages":   [{"page", "width", "height", "columns", "column_bands", "gutters",
               "text_layer_chars", "dropped_running_chars", "dropped_running_text",
               "n_blocks", "n_lines", "body_size", "empty", "cols_derived"}],
  "sections":[{"id", "title", "level", "page", "bbox", "block_id", "path"}],
  "metadata":{"title": {"text", "page", "bbox"}, "title_text", "authors": [str],
              "affiliations": [{"text", "page", "bbox"}], "emails": [str],
              "abstract", "abstract_pages", "keywords"},
  "references":[{"id", "text", "page", "bbox"}],
  "tables":  [{"id", "page", "bbox", "caption", "n_rows", "n_cols", "header", "rows",
               "body_rows", "cells", "bbox_cells", "fill_rate", "method",
               "absorbed_blocks", "unassigned_lines", "n_unassigned", "csv"}],
  "tables_rejected":[{"page", "bbox", "rejected"}],
  "figures": [{"id", "page", "bbox", "caption", "artwork", "width", "height", "image"}],
  "blocks":  [{"id", "page", "order", "page_order", "column", "type", "text", "raw",
               "bbox", "n_lines", "size", "bold", "italic", "mono", "font",
               "sup_sub", "rotated", "figure_id", "table_id", "masked_chars",
               "level", "bbox_source", "source", "confidence"}],
  "stats":   {"n_blocks", "types", "char_recall", "char_recall_vs_full_layer", "…"},
  "warnings":[], "selfcheck": {"errors": [], "warnings": [], "ok": true},
  "artifacts": {}
}
```

`blocks[]` 里带 `figure_id`/`table_id` 的分别指向 `figures[]`/`tables[]`；`masked_chars` 只在
`figure_label` 上出现；`level` 只在 `heading` 上出现；`bbox_source`/`source`/`confidence`
只由 OCR 分支写入。`text`/`raw` 的区别是：`text` 已做行拼接（连字符断行按原文保留），
`raw` 保留原始换行。

`type` 取值：`title / heading / body / caption / footnote / table / figure / formula /
reference / author / affiliation / code / figure_label / margin_artifact`。

- `figure_label`、`margin_artifact` 是**刻意不进正文**的块：图内坐标轴文字、图例、arXiv 水印、版权行。
  它们仍在 `blocks` 里（可核对"没丢，只是归类为图内文字"），`masked_chars` 记录被排除的字符数。
- `column = -1` 表示跨栏块（标题、通栏图表）。
- `sup_sub = "sup"|"sub"`：该块整体是上/下标；行内上下标在 `raw` 里保留原字形。
- `bbox` 一律是 PDF 坐标（左上原点，单位 pt），与 `overlay/` 上的画框完全对齐；OCR 块为 `null`。
- `tables[].cells` 是二维文本数组；`bbox_cells` 是 `[{"row","col","bbox"}]`，可逐格回页核对。
  表格区域里未落进网格的文字进 `unassigned_lines`（`n_unassigned` 计数），保证不漏字。

### 4.2 `text.md`

按 `page → 阅读顺序` 排列，块前一行 HTML 注释给出来源定位：

```
<!-- p3-b007 | type=body | col=1 | bbox=309.1,412.0,545.3,486.7 -->
```

标题按 `level` 映射为 `##`/`###`/`####`；表格块渲染为 `[table T3]` + 行文本（单元格用 ` | ` 分隔）；
图块渲染为 `![caption](figures/F2.png)`；公式块渲染为 `$$ … $$`。
`figure_label` / `margin_artifact` 不写入正文；正文里原本以 `#` 开头的行会被转义成 `\#`，
以免被 Markdown 误认成标题。

### 4.3 `report.json`

`input{path,sha256,bytes,pages}` + `engine` + `document` + `stats`（同 doc.json）+ `warnings[]`
+ `selfcheck{ok, errors[], warnings[]}` + `pages[{page, columns, gutters, text_layer_chars, n_blocks, empty}]`。
`selfcheck.errors` 非空时退出码为 4，说明产出**不能直接当结论用**，必须按 §7 处理。

`warnings[]` 是**文档级**提示（不影响自检），常见 `code`：

| code | 含义 | 该怎么办 |
|---|---|---|
| `title_merged` | 标题跨多行，已并回一块（否则第二行会变成假章节） | 无需处理；`metadata.title.text` 即完整标题 |
| `heading_merged` | 有标题以连接词结尾（for/of/the…），已把续行并回 | 无需处理；`sections` 里不会再出现半句标题 |
| `column_template_mismatch` | 双栏文档里某些页只判到 1 栏 | 看 `overlay/page-XX.png` 复核该页顺序 |
| `ocr_required` | 有页没有文本层 | 走 §6 OCR 分支，不要拿空结果交付 |

## 5. 工作流（Agent 应执行的步骤）

1. **探测**：`python scripts/parse_pdf.py paper.pdf --out out/paper --no-overlay --pages 1-2`
   —— 先只跑两页，确认它不是扫描件（退出码 0）且 `pages[].columns` 与肉眼一致，再全量跑。
   ⚠️ 页眉判定依赖**跨页重复**，只跑 2 页时页眉可能不会被剔除；探版只看版面，正式结果必须全量跑。
2. **全量**：去掉 `--pages` 跑完整文档；失败按退出码分流（见 §7）。
3. **验版**（必做，成本最高的错误都在这里）：
   - 看 `report.json.selfcheck`：`errors` 必须为空；
   - 看 `stats.char_recall`：应落在 `0.95–1.05`（<0.95 说明有文字没被任何块接住；>1.05 说明同一段文字被重复输出）；
   - 抽 `overlay/page-01.png`、`page-02.png`：栏线是否落在真实栏间空白、块的阅读序号是否呈"先左栏到底、再右栏"；
   - 抽 `text.md` 的头两页：标题/作者/摘要/1 引言 顺序是否正确，页眉页脚是否已从正文消失。
4. **取值**：从 `doc.json` 里按 `type`/`sections[].path` 取需要的部分；表格优先用 `tables/T*.csv`，
   单元格的 `bbox_cells` 可回到页面坐标核对。
5. **报告**：交出结构结果时，同时交出 `stats.char_recall`、`selfcheck`、以及**被标记为不确定的页/块**
   （例如 `pages[].empty == true`、`tables_rejected`、`n_unassigned > 0` 的表）。
6. **（可选）自证增益**：`python scripts/baseline_compare.py paper.pdf --doc out/paper/doc.json`
   —— 同一份 PDF 上，把"裸 Agent 的 `page.get_text()` 纯文本"与本引擎逐项对比
   （章节数、表/单元格、可定位块、图内文字混入、页眉残留、跨栏交错）。判据全部由 PDF 几何独立计算，
   数字可以直接写进交付说明，不需要形容词。逐例结果在 `results/baseline.json`
   （属于作者证据，不随 Skill 分发；Skill 本体只依赖 `scripts/baseline_compare.py`）。

## 6. 扫描件 / 无文本层（OCR 分支）

`parse_pdf.py` 退出码 `3` 或 `pages[].empty == true` 时：

```bash
python scripts/ocr_pages.py paper.pdf --out out/paper --dpi 200
```

它产出：

| 文件 | 用途 |
|---|---|
| `ocr/page-XX.png` | 该页渲染图（默认 200 dpi） |
| `ocr/prompt-XX.md` | 该页的转录指令（8 条纪律：逐字、保留连字与希腊字母、上下标、页眉页脚单列、表格用 Markdown、图/公式用占位符、不确定写 `[unreadable]`、首行 `## page N`、末行 `confidence:`） |
| `ocr/prompt.md` | 汇总清单 |
| `ocr/index.json` | `pages[{page, image, prompt, transcript}]` |

**由具备视觉能力的模型**按 `prompt-XX.md` 转录 `page-XX.png`，把结果写进 `ocr/page-XX.txt`，然后：

```bash
python scripts/merge_ocr.py out/paper --require all      # 全部页都必须有转录
python scripts/merge_ocr.py out/paper --pages 1-3        # 只合并部分页
```

合并后的块：`id = pN-vNNN`、`bbox = null`、`bbox_source = "vision"`、`source = "vision"`、
`confidence = high|medium|low`；`pages[].ocr = true`（附 `ocr_confidence`）；
`stats.ocr_pages` / `stats.ocr_blocks` 记录参与页数与块数，**`stats.char_recall` 为 `null`**
（没有文本层就没有分母，不要伪造召回率）。
**纪律**：模糊到无法辨认的行写 `[unreadable]`，绝不编造文字；坐标不能编造。

## 7. 异常处理

| 现象 | 判据 | 处理 |
|---|---|---|
| 无文本层（扫描件） | 退出码 3 / `pages[].empty` | 转 §6 OCR 分支；不要把空 doc 当结果提交 |
| 加密/损坏 / 0 字节 / 伪 PDF | 打开失败、`needs_pass`、`page_count == 0`，退出码 **2**，stderr 带原因 | 如实报告"无法解析"，给出 PDF 元信息（页数、大小）；不要重建内容，也不要落到 OCR 分支 |
| 0 页 / 截断到无完整页 | `page_count == 0` 或解析后没有任何页，退出码 **2** | 同上；不要把空 `doc.json` 当结果 |
| 解析中途异常（能打开、失败在页面级） | 退出码 **3**，stderr 带异常 | 报告"部分可解析"：交出已完成的页与 `warnings`，不要补齐未解析的页 |
| 参数非法（`--pages 1-x`、文件不存在） | 退出码 **2**，stderr 一行原因 | 直接改参数重跑，不要重试同一命令 |
| 分栏判错 | `report.json.pages[].columns` 与 overlay 不符 | 用 `--pages` 单页重跑确认；在结果里把该页标 `uncertain`，并把 `column_template` 与 `cols_derived` 一起交出 |
| 表格连成一片 | `tables_rejected` 有项 / `fill_rate < 0.4` | 该区保留为正文文本（不漏字），把 `unassigned_lines` 一并交出；不要硬造行列 |
| 文字重叠（双栏误并） | `char_recall > 1.05` | 大概率是同一行被两块接住；按 overlay 人工确认后报告，不要删块 |
| 页数极多（>200 页） | 解析时间线性增长 | 用 `--pages` 分批跑，各自出目录；汇总时保留每批的 `stats.n_pages_parsed` |

## 8. 自检清单（交付前逐条过）

- [ ] `selfcheck.ok == true`（否则先修，别交付）
- [ ] 有文本层时 `0.95 <= stats.char_recall <= 1.05`；OCR 模式下 `char_recall` 为 `null` 且 `stats.ocr_pages` 非空
      （定义：`emitted_chars / (text_layer_chars − dropped_running_chars − masked_figure_label_chars)`；原始口径 `char_recall_vs_full_layer = emitted_chars / text_layer_chars` 用于看有没有丢字）
- [ ] `blocks_with_bbox == n_blocks`（纯文本层文档）；OCR 模式允许 `blocks_with_bbox < n_blocks`
- [ ] 每页 `columns` 与 overlay 一致；跨栏块 `column == -1`
- [ ] `sections[].path` 的层级与页面上编号一致（3.2 在 3.3 之前）
- [ ] 表格 `n_rows × n_cols` 与肉眼一致；`tables_rejected` 是否可接受
- [ ] 被排除的块只有 `figure_label` / `margin_artifact`，没有被误排的正文
- [ ] 输出里出现的不确定项都已写进报告（不隐瞒）

## 9. 边界与已知限制

- 公式只做**区域识别 + 原文搬运**（`type=formula`），不做 LaTeX 语义转换；行内公式留在正文原字形里。
- 连字（ﬁ/ﬂ）与连字符断行**按原文保留**，便于逐字核对；需要归一化时在消费端处理。
- 旋转文字（侧边水印、竖排标题）归入 `margin_artifact`，不参与阅读顺序。
- 三栏：合成三栏页已通过（`columns=3` / `column_template=3` / 三个编号标题进 `sections` / `char_recall=1.0` / 栏序 0→1→2）；**真实期刊三/四栏未验证**，页眉页脚区跨栏块较多时仍可能只判到 2 栏，需 overlay 复核。
- **混合栏数文档**（正文单栏、附录双栏，如 ICLR 模板）：`pages[].columns` 逐页不同，跨栏不变式按页生效；
  汇总时请以 `pages[]` 为准，不要只信 `document.column_template`。
- 章节识别覆盖两种常见排版：编号 + 字号/字重变化，以及**正文号字号的全大写编号小节**（`3.1 VISION TRANSFORMER (VIT)`）；
  无编号、无字号差异、又与正文同字重的"暗标题"仍可能被当正文（此时 `sections` 会少，但文字不丢）。
- **中文**：编号标题（`1 引言`、`2.1 检索增强`）、无空格断行拼接、中文表格已在合成双栏语料上验证；
  未在真实中文期刊 PDF 上验证，竖排或中英混排的复杂版式请用 overlay 复核。
- **图/表栏号按几何重算**：完全落在一栏内的图/表归该栏（否则会被当成带区分界，抢到同带正文之前）；
  跨栏图仍是带区分界。图区 bbox 判错时栏号也会错，需 overlay 复核。
- 表格嵌套（单元格内含多行多列）按单元格内多行文本保留，不展开为子表。
- 作者顺序按页面行序，个别版式（作者分列排版）可能与阅读顺序不一致，需人工确认。
- 只处理 PDF；DOCX/HTML 请先用 office/latex 工具链转 PDF。

## 10. 版本与来源

- `pdf-struct/2`，脚本 `scripts/pdf_struct.py` + `scripts/parse_pdf.py`（本 Skill 自带，无外部服务）。
- 工具箱：`scripts/parse_pdf.py`（主入口）、`scripts/pdf_struct.py`（引擎）、
  `scripts/ocr_pages.py` + `scripts/merge_ocr.py`（扫描件分支）、`scripts/run_case.py`（平台入口）、
  `scripts/baseline_compare.py`（与裸 dump 的量化对照，可选）。
- 自测：`python tests/test_engine.py`（27 条，中文双栏 / 跨行标题 / 扫描件）+ `python tests/test_robustness.py`
  （54 条，0 字节/伪 PDF/截断/加密/0 页/单页/旋转/三栏/坏参数），共 **81 条**，不依赖 pytest、不联网。
  改引擎前后都应跑一遍。
- 依赖：PyMuPDF 2.1（MuPDF 1.28.6，AGPL，仅本地解析，不联网）、Pillow 12.3（overlay 与裁图）。
- 算法与取舍见 `references/method.md`；schema 逐字段说明见 `references/schema.md`。
- 示例调用与示例输出见 `examples/`（`quickstart.md` 是一屏接入版；示例仅用于说明调用方式，不是正式用例结果）。