# 输出契约：`doc.json` 字段参考（schema `pdf-struct/2`）

除特别注明外，坐标单位是 PDF 点（pt），原点在页面左上角，`bbox = [x0, y0, x1, y1]`。

## 顶层

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema` | str | 固定 `"pdf-struct/2"`；字段变动会升版本号 |
| `source` | obj | `path`（仅文件名）、`sha256`、`bytes`、`pages` |
| `engine` | obj | `name`、`version`（PyMuPDF）、`mupdf`、`python`、`pipeline` |
| `document` | obj | `pages`、`column_template`（文档级栏数）、`has_text_layer` |
| `pages[]` | obj | 逐页信息，见下 |
| `sections[]` | obj | 章节树，见下 |
| `metadata` | obj | 标题/作者/机构/摘要/关键词 |
| `references[]` | obj | 参考文献条目 |
| `tables[]` | obj | 通过合理性闸门的表格；未通过的进 `tables_rejected[]`（带 `rejected` 原因） |
| `figures[]` | obj | 图区 |
| `blocks[]` | obj | **唯一的正文承载结构**，按阅读顺序排列 |
| `stats` | obj | 统计与字符对账 |
| `warnings[]` | obj[] | 执行期告警（不影响退出码）：`{code, detail, …}`，`code ∈ {title_merged, heading_merged, column_template_mismatch, ocr_required}` |
| `selfcheck` | obj | `{errors[], warnings[], ok}`；`ok=false` 时进程退出码 4 |
| `artifacts` | obj | 生成的附属文件路径（tables/figures/overlay/text.md） |

## `pages[]`

`page`（1 起）、`width`、`height`、`columns`（本页判定栏数）、`column_bands`（每栏 x 区间）、
`gutters`（栏间空白 x 区间）、`text_layer_chars`、`dropped_running_chars`（被判为页眉/页脚而剔除的字符）、
`dropped_running_text[]`（被剔除的原文，便于核对是否误删）、`n_blocks`、`n_lines`、`body_size`（正文主字号）、
`empty`、`cols_derived`（仅当栏数继承自文档模板时出现，值为 `"document_template"`）、
`ocr`/`ocr_confidence`（仅 OCR 分支写入）。

## `blocks[]`

| 字段 | 含义 |
|---|---|
| `id` | 形如 `p3-b004`（页-页内序号），稳定可引用 |
| `page` | 1 起页码 |
| `bbox` | 页面坐标；视觉转录块为 `null`，同时 `bbox_source="vision"` |
| `column` | 栏序号；跨栏块为 `-1` |
| `type` | 见下表 |
| `text` | 文本；表格块为多行、**单元格用 ` \| ` 分隔**、行间 `\n`；图块为 `""` |
| `raw` | 未做行拼接的原始行文本（保留换行，便于核对连字符与断行） |
| `n_lines` | 原始行数 |
| `size` / `font` / `bold` / `italic` / `mono` | 首行主导字体属性 |
| `sup_sub` | `"sup"` / `"sub"` / `null`（上下标单独成行时标记） |
| `rotated` | 旋转文本（侧边水印）为 `true` |
| `order` | 全局阅读顺序（0 起，连续） |
| `page_order` | 页内阅读顺序 |
| `masked_chars` | 仅 `figure_label`：被遮蔽而不进正文的字符数 |
| `level` | 仅 `heading`：章节层级（1 起），与 `sections[].level` 一致，`text.md` 据此渲染 `##`/`###`/`####` |
| `figure_id` / `table_id` | 仅 `figure` / `table` 块：指向 `figures[]` / `tables[]` 的 id |
| `source` / `confidence` | 仅 OCR：`"vision"` 与 `high/medium/low` |

### `type` 取值

| 值 | 语义 | 是否进 `text.md` 正文 |
|---|---|---|
| `title` | 论文标题 | 是（作为一级标题） |
| `author` / `affiliation` | 作者、机构 | 是 |
| `heading` | 章节标题（`level` 见 `sections`） | 是 |
| `body` | 正文段落 | 是 |
| `abstract` | 摘要（也以 `body` 存储，`metadata.abstract` 为汇总） | 是 |
| `caption` | 图表标题 | 是 |
| `table` | 表格块 | 是（`[table Tn]` + 行文本，单元格 ` \| ` 分隔） |
| `formula` | 公式（文本形式，不做 LaTeX 重排） | 是 |
| `reference` | 参考文献条目 | 是 |
| `footnote` | 脚注 | 是（标注为脚注） |
| `figure` | 图区（`text` 为空，`caption` 在图注块） | 仅插图 |
| `figure_label` | 图内文字（坐标轴刻度/图例/结构标注） | **否**，但保留在 `blocks` 里可核对 |
| `margin_artifact` | 页眉页脚、arXiv 水印、版权许可、旋转水印 | **否**，原文见 `pages[].dropped_running_text` |

## `figures[]`

`id`（`F1..`）、`page`、`bbox`（图注 ∪ 图区）、`caption`（图注原文）、
`artwork`（`raster` 位图 / `vector` 矢量簇 / `caption_only` 只有文字图注）、
`width`/`height`（图区像素）、`image`（`figures/F1.png` 裁剪路径，`--no-figures` 时为 `null`）。

## `tables[]`

`id`（`T1..`）、`page`、`bbox`、`n_rows`、`n_cols`、`fill_rate`（非空单元格比例）、
`method`（`pymupdf_find_tables`）、`header`（首行）、`rows`（全部行，`\t` 分隔）、`body_rows`、
`cells`（二维文本数组）、`bbox_cells[]`（每个单元格 `{row, col, bbox}`，可逐格回页）、
`caption`（表格区域内的标题行，若有）、`absorbed_blocks`（被并入该表的正文块数）、
`unassigned_lines[]`/`n_unassigned`（区域内未落进网格的原文，保证不漏字）、
`csv`（`tables/T1.csv`）。

## `sections[]`

`id`、`title`、`level`（1–3）、`page`、`bbox`、`block_id`（对应 `blocks[].id`）、
`path`（层级路径，父标题与自身标题用 ` / ` 连接，如
`3. Deep Residual Learning / 3.1. Residual Learning`，可直接做层级导航）。
父子关系由 `level` + `path` 表达——不另存 `parent` 字段，避免两处状态不一致。

## `references[]`

`id`（`R1..`）、`text`（条目全文，跨行已拼接）、`page`、`bbox`。

## `metadata`

| 字段 | 形态 | 说明 |
|---|---|---|
| `title` | `{text, page, bbox, size} \| {}` | 标题对象；`{}` 表示未识别到。跨行标题已并成一条（`warnings[].code = title_merged`），`size` 是该标题的字号，也是章节层级的第一级刻度 |
| `title_text` | `str` | 上者的文本便利字段（等价于 `title.text`，无 title 时为 `""`） |
| `authors[]` | `str[]` | 逐个作者名 |
| `affiliations[]` | `[{text, page, bbox}]` | 机构（带定位） |
| `abstract` | `str` | 摘要正文（跨块拼接） |
| `abstract_pages[]` | `int[]` | 摘要所在页 |
| `emails[]` | `str[]` | 从作者区抽出的邮箱 |
| `keywords[]` | `str[]` | 关键词行（有则取） |

取不到时为空串/空数组/`{}`——**不做猜测性填充**。

## `stats`（字符对账，判断"提得全"的核心）

```
text_layer_chars      文本层字符总数（去空白）
dropped_running_chars 判为页眉/页脚而剔除的字符
masked_figure_label_chars 图内文字（figure_label）的字符
emitted_chars         实际进入正文的字符
char_recall           emitted / (text_layer − dropped_running − masked_figure_label)   目标 ≥ 0.90，> 1.05 视为重复输出
char_recall_vs_full_layer emitted / text_layer                    仅作参考（图内文字本就不该进正文）
n_blocks / n_headings / n_formulas / n_tables / n_table_cells / n_figures / n_sections
blocks_with_bbox / blocks_with_page   自检用：应等于 n_blocks（视觉块单独计）
types                 各类型块计数
```

## `text.md`

按阅读顺序输出的人读版本，每个块前一行 HTML 注释携带溯源信息：

```markdown
<!-- p3-b004 | type=body | col=0 | bbox=50.0,120.0,286.0,150.0 -->
```

`figure_label` / `margin_artifact` 不写入正文（避免污染），但在 `doc.json` 中完整保留。

## 退出码

| 码 | 含义 | 调用方应有的反应 |
|---|---|---|
| 0 | 成功且 `selfcheck.ok` | 直接使用 |
| 2 | 参数错误 | 修正命令行 |
| 3 | 无文本层（整篇扫描件） | 走 OCR 分支（`ocr_pages.py` → 转录 → `merge_ocr.py`） |
| 4 | 自检未通过 | 读 `selfcheck.errors`，结果不可直接采信，报告中须标 `partial` |

## `report.json`

`doc.json` 的精简视图（输入指纹、引擎、统计、自检、逐页栏数），用于快速核对，
不含 `blocks`，因此体积小、可安全贴进日志。

## `ocr/index.json`

OCR 分支的清单：`{schema, pages: [{page, image, prompt, transcript|null, confidence}]}`；
`merge_ocr.py` 依据它判断是否全部转录完成（`--require all`）。