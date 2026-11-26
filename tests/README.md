# tests/ —— 三个合成 fixture 与黑盒回归

这个目录补上 SKILL.md 里**声称支持、但此前从未被验证**的两块能力：

1. **中文双栏** + **两行标题合并** + **全大写正文号的二级标题**（`pdf-struct/2` 的三个
   结构不变式）。
2. **无文本层扫描件**走 `ocr_pages.py` → 视觉转录 → `merge_ocr.py` 的整条分支，
   以及合并后 `bbox:null / bbox_source:"vision"` 的契约。

它**不**证明任何模型识别率，也**不**证明引擎在真实期刊排版上的普适性（见"合成声明"）。

---

## 1. 三个 fixture 分别证明什么

| fixture | 构造 | 被固化的断言 |
|---|---|---|
| `cjk-2col.pdf` | A4 单页。通栏中文标题、一条通栏作者/单位带、`摘要`、通栏关键词；下方双栏：左栏 `1 引言` / `2 相关工作` / `2.1 检索增强`，右栏 `3 方法` / 3×3 中文表格（矢量线框）/ `图 1 系统结构` 图注 / `4 实验` / `参考文献`。中文用系统字体嵌入，**有真实文本层**。 | 正文页 `pages[].columns == 2`；`sections[].path` 里出现 `1 引言` 与 `2 相关工作 / 2.1 检索增强`；`0.90 ≤ stats.char_recall ≤ 1.05`；`selfcheck.ok == true`；3×3 表格被结构化（`n_rows == 3, n_cols == 3`），若被拒则要求 `tables_rejected` 非空且 9 个单元格文字仍留在正文；没有任何 `column ≥ 0` 的块跨过 gutter。 |
| `title-wrap.pdf` | US Letter 单栏。标题排两行、**第一行以冒号结尾**；作者行带逗号；`Abstract`；三节，其中 `2.1 SETUP AND METRICS` 与正文**同字号、全大写、不加粗**（ICLR camera-ready 风格）。 | `metadata.title.text` 同时含两行标题文字；`warnings[].code` 含 `title_merged`；`2.1 SETUP AND METRICS` 存在且 `level == 2`；**不**存在标题等于第二行文字的假章节。 |
| `scanned.pdf` | 把 `title-wrap.pdf` 的页面渲染成 200dpi PNG，再单独组一个**只有图像**的单页 PDF（生成器里断言 `page.get_text()` 为空）。 | `parse_pdf.py` 退出码必须是 `3`；`ocr_pages.py` 产出 `ocr/page-01.png`、`ocr/prompt-01.md`、`ocr/index.json`；写入 `ocr/page-01.md` 后 `merge_ocr.py --require all` 退出码 `0`；合并后所有块 `bbox == null`、`bbox_source == "vision"`、`confidence` 非空；`stats.char_recall is None`；`stats.ocr_pages` 覆盖第 1 页。 |

## 2. 合成声明（重要）

- 三个 PDF 都是 `outputs/scripts/make_fixtures.py` **现造**的：不是任何真实期刊页面、
  不是真实扫描件、不是任何比赛的原始语料。字体是 Windows 自带的 `msyh.ttc`
  （缺失时退到 `simsun.ttc`），只做子集嵌入，所以文件很小。
- 因此 `cjk-2col` 的中文双栏只覆盖"投影能分开的干净双栏"，不覆盖倾斜扫描、
  跨栏公式、竖排、脚注穿插等真实难点；`title-wrap` 的标题风格是手写的 ICLR 近似。
- **`scanned` 用例验证的是"合并管线"，不是视觉模型识别率。**
  写进 `ocr/page-01.md` 的转录文本，是生成该页时使用的**已知源文本**
  （`test_engine.py` 直接从 `make_fixtures` 的常量取，非人工抄写）。
  合成页的真值已知，所以这一步能严格检查 `merge_ocr.py` 的字段契约；
  它**不能**说明任何 OCR/视觉模型在这个页面上的准确率。
  本项目**没有**做过真实扫描件的 OCR 识别，也不声称做过。
- 生成是确定性的：`no_new_id=True, reproducible=True` 保存，同一台机器上
  重复运行得到的三个 PDF **字节级一致**（同字体、同 PyMuPDF 版本）。

## 3. 怎么跑

```bash
# 唯一可用的解释器
PY="C:/Users/mzn/AppData/Local/Programs/Python/Python313/python.exe"

# 1) 生成三个 fixture（幂等，可反复跑）
"$PY" outputs/scripts/make_fixtures.py
#    -> tests/fixtures/{cjk-2col,title-wrap,scanned}.pdf

# 2) 跑全部断言（不需要 pytest；fixture 缺失时会自动先生成）
"$PY" tests/test_engine.py
#    只跑某几个： test_engine.py cjk / title / scanned

echo $?          # 0 = 全绿，1 = 有 FAIL
```

- 屏幕输出是**纯 ASCII**（目标机器控制台是 GBK，中文 `print` 会炸）。
  中文标题以 `\uXXXX` 转义显示，保证期望值精确可核对。
- 每次运行的明细（UTF-8，含中文原文）写在 `tests/_work/last_run.txt`；
  中间产物在 `tests/_work/{cjk,title-wrap,scanned}/`，删掉即可重来。
- `tests/_work/` 是生成物目录，可随时删除；`tests/fixtures/` 可以保留入库，也可以删掉后重新生成。

## 4. 断言失败意味着什么

**cjk-2col**

| 失败断言 | 说明 |
|---|---|
| `body page columns==2` | `detect_columns()` 没识别出栏间空白。常见原因：跨栏的通栏行（标题/摘要/作者带）被算进了"短行投票"，或 gutter 里出现了 ≥2 条短行。这是最上游的错误，后面几条会连带失败。 |
| `section path has '1 引言'` | 中文编号标题没被 `classify()` 认成 heading（`NUM_HEAD_RE`/`CN_HEAD_RE` 或字号/加粗门槛），或者它被并进了上一段。 |
| `section path has '2 相关工作 / 2.1 检索增强'` | 层级错了：`heading_level()` 对 `2.1` 应给 2；若给出 1，说明 `2 相关工作` 根本没进栈（不是 heading），路径就变成平铺。 |
| `0.90 <= char_recall <= 1.05` | 有文字没进 `blocks`（<0.90：段落被吞、表格被吸收但没输出），或重复计数（>1.05：同一段被两个块各算一次，常见于 gpt3 那类公式页）。**这条是"不许凭空消失"的硬闸门。** |
| `selfcheck.ok` | 引擎自检的硬违规：`no_blocks` / `block_without_bbox` / `order_not_contiguous` / `column_block_crosses_gutter` / `bbox_coverage_incomplete`。看 `doc.json.selfcheck.errors`。 |
| `3x3 table structured` | `find_tables()` 没抓到网格。此时必须走另一条分支（`tables_rejected` + 文字仍在正文），否则表格文字就丢了。 |
| `table rejected but its text kept in body` | 最危险的一种：网格没识别、**且**单元格文字也没进正文——即"字被吞了"。 |
| `no column block crosses the gutter` | 一个被归到左/右栏的块，横向跨过了 gutter：阅读顺序必然出错。 |

**title-wrap**

| 失败断言 | 说明 |
|---|---|
| `metadata.title.text holds both title lines` | `merge_title_continuations()` 没把第二行并进标题（它要求同字号、紧邻、无逗号/分号、不以句号结尾）。 |
| `warnings include title_merged` | 同上，只是从告警面看：这条告警是"发生过合并"的可观测证据，缺了说明合并没触发。 |
| `'2.1 SETUP AND METRICS' is a level-2 section` | 全大写、正文号的编号小节没被 `classify()` 的 caps 分支接住（会退化成 body 或 1 级）。 |
| `no phantom section from title line 2` | 标题第二行自己变成了章节——即上面合并失败的后果。 |

**scanned**

| 失败断言 | 说明 |
|---|---|
| `parse_pdf exit=3` | 引擎认为这页"有文本层"。要么 fixture 坏了（PNG 里带了文本），要么退出码语义被改坏。 |
| `ocr_pages wrote ocr/...` | 渲染/提示生成分支坏了。 |
| `merge_ocr --require all exit=0` | 最常见原因：转录文件扩展名没被认（`page-01.md` vs `page-XX.txt`）、`confidence:` 行缺失、或缺页。退出码 `2` = 找不到/缺转录。 |
| `every merged block has bbox=null` / `bbox_source=vision` | 视觉块被塞了伪造的坐标——这是"不许编造"的红线。 |
| `every merged block has a confidence` | 转录里没有 `confidence:` 行，或解析没落到块上。 |
| `stats.char_recall is None` | 无文本层的页不该有字符召回率；非 None 说明拿 0 除了或者拿了伪造分母。 |
| `stats.ocr_pages covers page 1` | 合并没记账（`ocr_pages` 是页号列表，断言用 `len(...)>=1 and 1 in ...`）。 |

## 5. 本轮修掉的三个引擎问题

### 5.1 扫描件转录文件名（`merge_ocr.py` / `ocr_pages.py`）

`merge_ocr.py` 原来只 glob `ocr/page-*.txt`，而 `outputs/examples/README.md` 与 SKILL.md
的流程都让操作者写 `ocr/page-01.md` —— 照文档做，合并端会以退出码 2（"no transcripts found"）失败，
**整条扫描件分支此前从未真正可用**。现在两种扩展名都接受（`.txt` 优先，保证确定性），
`ocr_pages.py` 的提示语与 `index.json.transcript_exists` 同步。由 `scanned` fixture 端到端锁住。

### 5.2 栏内图/表被排到正文之前（`pdf_struct.py::order_blocks`）

`parse_document()` 里图/表块硬编码 `column: -1`（未知）。`order_blocks()` 在同一个 band 内按
`column` 升序输出，于是 `-1` 的图/表会**抢在同 band 的左栏正文之前**：ResNet 第 1 页的图 1
（右栏 y≈224）曾排在 `1. Introduction` 之前，`cjk-2col` 的 `p1-b005/p1-b006` 也曾先于 `p1-b007`。

修法：在 `order_blocks()` 里对 `column < 0` 且**不跨 gutter** 的块，用 `column_of()` 按几何重算栏号。
跨栏图仍是带区分界，行为不变。修完 ResNet 第 1 页的顺序变成
「左栏标题/正文/脚注 → 右栏图 1 → 右栏正文」，五篇语料的
`n_blocks / n_sections / n_headings / n_tables / n_figures / char_recall / types` **全部 identical**
（只有块序、块 id、overlay 上的序号变了）。

### 5.3 图注在 `text.md` 的 alt 文本里被静默截断（`parse_pdf.py`）

`write_text_md()` 原来把图注 `[:80]` 硬切，`![...](figures/F1.png)` 里的句子会断在半句
（ResNet 图 1 的 alt 只剩 `... with 20-layer`）。现在 alt 文本保留**完整图注**（只做空白折叠与 `]` 转义），
紧随其后的 `caption` 块仍是权威文本。代价是图注在 `text.md` 里出现两次，换来"没有半句被吃"。

## 6. 已知但**未**修的问题

- **图区上沿判偏时，边缘轴标可能漏遮罩**：ResNet p2 的 `x`（`p1/p2` 轴标）因图区上沿差 ~0.5pt
  被当成 `body` 留在正文里。字符账仍闭合（`char_recall` 不受影响），已在
  `outputs/response.md` §6 显式声明，没有靠改口径掩盖。
- **真实视觉模型的 OCR 识别率**：本目录只验证管线，不做识别率评测。
- **3 栏以上正文、无框线表格、嵌套表**：`characterization.json` 里标为 declared / untested。

## 7. 复现与产物

- `tests/fixtures/` 的三个 PDF 由 `outputs/scripts/make_fixtures.py` 生成，确定性、可删后重建；
  它们**不随 `results/` 记账**，也不冒充真实语料。
- 运行产物写到 `tests/_work/`（不随包分发）：`last_run.txt` 是 UTF-8 明细，
  `{cjk,title-wrap,scanned}/` 是每次解析的中间结果，删掉即可重来。
