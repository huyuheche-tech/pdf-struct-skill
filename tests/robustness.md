# tests/robustness.md —— 异常输入 × 退出码 × 三栏版面的证据

这一页只回答两个此前"已声明、未验证"的问题：

1. **坏输入**会不会把 Python traceback 抛给用户？退出码与 `outputs/SKILL.md` 写的一致吗？
2. **三栏正文**到底判成几栏？阅读顺序对吗？文字丢没丢？

全部证据由 `python tests/test_robustness.py` 现造、现跑（54 条断言，纯 python，无 pytest、无网络），
本文件是那次运行的文字化记录。三栏 fixture 由测试现场生成，不随包分发。

```bash
PY="C:/Users/mzn/AppData/Local/Programs/Python/Python313/python.exe"
"$PY" tests/test_robustness.py            # 54 checks, 0 failed
"$PY" tests/test_robustness.py three      # 只跑某一个 case
```

判定口径（两条都必须满足，缺一即 FAIL）：

- **(a) 退出码**等于 SKILL.md 声明的值（或落在声明区间内）；
- **(b)** stdout+stderr 里没有 `Traceback (most recent call last)`，且 stderr 有可读英文原因
  （§7 原文："stderr 带异常信息"）。

**本轮没有把任何断言改松来换全绿。** 唯一那条 FAIL 是真实缺陷，最小复现写在 §3.3，
按"改动会让 `work/regress.py` 的指标变化就回退"的约束**没有修**。

---

## 1. 「期望退出码 → 实际退出码」总表

| # | case | 期望退出码（引 SKILL.md 原文） | 实际退出码 | traceback | 断言结论 |
|---|---|---|---|---|---|
| 1 | `zero-byte.pdf`（0 字节） | **2** —— §7"加密/损坏 \| 打开异常，退出码 2，stderr 带异常信息" | **2**（修复前 **3** ✗） | 无 | PASS |
| 2 | `not-a-pdf.pdf`（纯文本改扩展名） | **2** —— §7 同上"损坏" | **2**（修复前 **3** ✗） | 无 | PASS |
| 3 | `truncated.pdf`（`corpus/resnet.pdf` 前 40% 字节） | **2**（§7 损坏）；若 mupdf 能修复出完整页，则允许 **0/4** 且必须带 `warnings` | **2**（0 页，拒绝解析） | 无 | PASS |
| 4 | `encrypted.pdf`（AES-256，`user_pw` 必需） | **2** —— §7"加密/损坏 \| 打开异常，退出码 2" | **2**（修复前 **3** ✗） | 无 | PASS |
| 5 | `one-page.pdf`（单页、无页眉） | **0** —— §2"`0` 成功" | **0**；`selfcheck.ok=true`、`char_recall=1.0`、`dropped_running_chars=0`、`columns=1` | 无 | PASS |
| 6 | `rotated.pdf`（`/Rotate 90`） | **0** —— §2"`0` 成功" | **0**；`char_recall=1.0`，24 行正文一行不少 | 无 | PASS |
| 7 | `three-col.pdf`（3×60mm，栏距 6mm） | **0** —— §2"`0` 成功"；§9"三栏及以上：`column_template` 会给出实际栏数" | **0**；`columns=3`、`column_template=3`、`char_recall=1.0`、3 个编号标题全进 `sections` | 无 | **部分 PASS**：栏数/标题/召回/栏序四条必需项通过；同属 (d) 的一条加严项 **FAIL**（正文一行被甩到页尾，§3.3） |
| 8 | `empty.pdf`（0 页，`/Count 0`） | **2** —— §7"加密/损坏 \| 打开异常"；§2 的 `3` 专指"该 PDF 无文本层，必须转 OCR 分支"，0 页不可能 OCR | **2**（修复前 **3** ✗，还提示"use the OCR path"） | 无 | PASS |
| 9 | （附加）`--pages 1-x` | **2** —— §2"`2` 用法错误" | **2**（修复前：ValueError traceback） | 无 | PASS |

坏输入的实际 stderr（原样，全部 ASCII）：

```
zero-byte  ERROR: ...\zero-byte.pdf: cannot open PDF (EmptyFileError: Cannot open empty file: ...)
not-a-pdf  ERROR: ...\not-a-pdf.pdf: cannot open PDF (FileDataError: Failed to open file '...' as type pdf.)
truncated  ERROR: ...\truncated.pdf: PDF has 0 pages; nothing to parse (file may be truncated or corrupt)
encrypted  ERROR: ...\encrypted.pdf: PDF is encrypted; a password is required
empty      ERROR: ...\empty.pdf: PDF has 0 pages; nothing to parse (file may be truncated or corrupt)
bad-pages  ERROR: bad --pages value '1-x' (use 1-6 or 1,3,5)
```

四种坏输入都**没有**写出 `doc.json`：失败就是失败，不会留下"半个结果"让下游误当成功。

### 关于 `truncated.pdf` 的一条实测事实

`corpus/resnet.pdf` 取前 40%（135 KB / 339 KB）后，MuPDF 的修复模式把文件读成**0 页**——
它没有"解析出前几页"这种中间态。所以这个 case 走的是"干净失败 → 退出码 2"，
不是"部分成功 + warnings"。测试对两条路径都写了断言（`exit==2` 要 stderr 说明原因；
`exit in (0,4)` 要求 `n_pages_parsed>=1` 且 `warnings` 非空；`exit==3` 要求确有 `empty` 页
且带 `ocr_required`），本次实际落在第一条。语料不在包内时，同一个 case 改为截断现场生成的
6 页合成 PDF，逻辑不变。

---

## 2. 三栏版面的具体数字

fixture：A4 595×842，三个 **60 mm** 栏、**6 mm** 栏距（内容宽 3×60+2×6 = 192 mm，左右各 9 mm 边距）；
通栏标题/作者/单位/摘要，正文三栏各一个编号标题；正文**左对齐不两端对齐**（原因见 §3.4）。

| 指标 | 实测 | 结论 |
|---|---|---|
| `pages[0].columns` | **3** | 对 |
| `document.column_template` | **3** | 对 |
| `column_bands` | `[[25.4, 189.0], [211.0, 370.0], [398.0, 559.4]]` | 三条互不重叠、从左到右 |
| `gutters` | `[[189.0, 211.0], [370.0, 398.0]]` | 两条 gutter；第二条的右边缘被一条越界行占了 2.8 pt（§3.3） |
| `sections` | `1 INTRODUCTION` / `2 METHOD` / `3 RESULTS`，`level=1`，共 3 条 | 三个标题全部进树 |
| `stats.char_recall` | **1.0**（`emitted_chars == text_layer_chars`） | 不丢字 |
| `stats.n_blocks` | 17（4 heading + 1 author + 1 affiliation + **11 body**；其中 1 个 body 块是被误判的 §3.3） | 见 §3.3 |
| 块的 `column` 序列（col≥0） | `0,0,0,0,0` → `1,1,1,1` → `2,2,2` | 先读第 1 栏再第 2 栏，**没有** 1→3→2 |
| 栏内 `bbox.y0` | 每栏严格递增 | 栏内自上而下 |

必需的四条断言：(a) `columns=3` PASS；(b) 三个标题都在 `sections` PASS；
(c) `char_recall=1.0` PASS；(d) 按栏读、栏序不回退、栏内 y 单调 PASS。
同属 (d) 的一条加严检查 **FAIL**：`p1-b016` 被当成跨栏块排到整页最后（§3.3）。
**文字一个没丢**，但有一句话的阅读位置错了。

---

## 3. 本轮发现的问题

### 3.1 【真 bug，已修】加密/损坏/0 页被报成"无文本层，请走 OCR"

`SKILL.md` §7 写"打开异常，退出码 **2**，stderr 带异常信息"，但 `parse_pdf.py` 只有一个
`except Exception -> return 3` 的兜底，而且打在 **stdout** 上。实测（修复前）：

| 输入 | 修复前 | 文档 |
|---|---|---|
| 0 字节 | 3 + `ERROR: parse failed: EmptyFileError...`（stdout） | 2 + stderr |
| 纯文本 | 3 + `... FileDataError ...` | 2 + stderr |
| AES-256 加密 | 3 + `... ValueError: document closed or encrypted` | 2 + stderr |
| 0 页 | 3 + `NOTE: no text layer ... use the OCR/vision path` | 2 |

最后一行最糟：它把一个 0 页文件指去 OCR 分支，而 OCR 分支同样产不出任何页。

**改法**（`outputs/scripts/parse_pdf.py`）：
新增 `file_level_error()`（第 189–206 行），在解析前先做一次轻量 open：
打不开（`EmptyFileError` / `FileDataError`）→ 2；`needs_pass` → 2；
`page_count == 0` → 2。`main()` 在 `ensure_dir()` **之前**调用（第 282–285 行），
失败时 `sys.stderr.write` 后返回 2，因此不会留下空的输出目录或 `doc.json`。
`parse_document` 的兜底异常也改成写 stderr（第 291 行），退出码仍是 3（保留给"能打开但解析中途失败"）。

### 3.2 【真 bug，已修】`--pages 1-x` 直接抛 traceback

`int(b)` 没有保护，`ValueError` 冒到顶层，Python 打印 traceback 并 exit 1——既不是 0/2/3/4，
也没有可读原因。§2 明确"2 用法错误"。已加 `try/except ValueError → stderr + return 2`
（第 276–281 行）。这是第 9 个（附加）case 锁住的。

### 3.3 【真 bug，**已修**】栏内一条宽行被当成跨栏块，正文被甩到页尾

**现象**（唯一那条 FAIL，`three-col` case 的附加断言）：

```
FAIL  three-col  (d) no body block is emitted as cross-column
      [stray=[('p1-b016', -1, 212.5, 'median of three repeats is reported for')]]
```

`p1-b016` 的 `bbox.x0 = 212.5`，明明在第 2 栏（`column_bands[1] = [211.0, 370.0]`），
却因为 `bbox.x1 = 372.8` 比同栏其余行（最宽 368.8）宽了 4 pt、伸进 gutter
（`[370.0, 398.0]`）2.8 pt，被判成 `column = -1`；而 `order_blocks()` 把跨栏块当作
**带区分界**，会把它排在整页**最后**。结果 `2 METHOD` 里的一句话
"… and the | median of three repeats is reported for every point." 被拆成两块，
后半句掉到 `3 RESULTS` 之后。文字没丢（`char_recall` 仍是 1.0），但阅读顺序错了。

**根因**（两个函数的度量口径不一致）：

- `detect_columns()`（`pdf_struct.py:201–256`）用**墨迹投影**推栏边界：gutter 是
  "`cov[x] <= 1` 的连续条带"，因此栏的右边界 = **第二宽**那一行的右沿（370.0），
  而不是栏框的真正右沿（约 381.5）。它也刻意容忍"一条闯入者"。
- `order_blocks()`（`pdf_struct.py:638–673`）却把"跨过 gutter"一律当成**跨栏块**
  （带区分界，排到带末）。

于是"全栏最宽的那一行"（哪怕只比别人宽 2 pt、仍在自己的 60 mm 栏框内）必然被牺牲。
**这不是阈值问题，是算法问题**：栏的几何边界应该来自栏框/双向投影，而不是"哪一行最宽"。
真实排版里行内公式、长 em-dash、连字符都会制造这种"单行更宽"。

**尝试过的修法（在 `detect_columns()` 里把 gutter 收紧成真正无墨迹的子区间）与回退记录**：

| 版本 | 三栏 fixture | `work/regress.py` |
|---|---|---|
| 收紧条件 = 有任何重叠 | PASS | **FAIL**：`gpt3` `body 419→420, code 104→103`；`vit` `n_blocks 742→749, body 158→160, figure_label 383→388` |
| 收紧条件 = 侵入 ≥ 6 pt | **FAIL**（该行只侵入 2.8 pt） | **FAIL**：`gpt3` 同上；`vit` `n_blocks 742→743, body 158→159` |

按"五篇语料任一指标变化就回退"的约束，两种都**回退**了；`pdf_struct.py` 现在与改动前逐行一致。
所以这里保留 FAIL，并给出上面这条最小复现，而不是调松断言或改 fixture 去绕开它。

**最终修法（已实施，只改排序层，不动 `detect_columns()`）**：把"是否跨栏"从
"碰到 gutter" 改成**重叠率**判据——`column_overlap_ratio(bbox, bands) >= 0.80` 即认为该块属于
某一栏（`COLUMN_OWN_RATIO`），gutter 里那几 pt 墨迹只是字框侧边距（`GUTTER_INK_TOL = 4.0`）。
`order_blocks()` 与自检的 `column_block_crosses_gutter` **用同一个函数、同一个阈值**，
不再出现"归了栏又报跨栏"的自相矛盾。

| 版本 | 三栏 fixture | `work/regress.py` |
|---|---|---|
| 按"宽度 ≤ 最宽栏 + 8pt"判（第一版） | PASS | **FAIL**：`vit` 8 条 `column_block_crosses_gutter`（表行确实横跨两条被判出来的窄栏） |
| 按重叠率 ≥ 0.80 判（最终版） | **54 / 54 PASS** | **OK**：583 / 510 / 687 / 961 / 742 全不变 |

修完 `p1-b016` 归入第 2 栏、排在 `3 RESULTS` 之前，`2 METHOD` 的句子不再被拆到页尾。

### 3.4 为什么 fixture 不做两端对齐（如实说明）

最初的版本用 `insert_textbox(align=JUSTIFY)` 造"真期刊式"的两端对齐正文，结果 PyMuPDF 的
两端对齐会把某些行拉成 16 pt 的词间距，再次抽取时同一行被切成 `fixed` / `by` / `folklore`
三段（`merge_rows` 的 14 pt 阈值接不住）。那是**生成器**的失真，不是引擎的版面判断，
所以测试改成左对齐 + 按字宽换行（`wrap_width()` 用 `get_text_length` 保证每行 ≤ 栏宽）。
这恰好把 §3.3 那个真实缺陷暴露了出来。

### 3.5 【已修】0 页这件事 SKILL.md 没有单列

`SKILL.md` 原来只列了"加密/损坏 → 2"。已在 §7 补三行：「0 页 / 截断到无完整页 → 2」、
「解析中途异常 → 3」、「参数非法 / 文件不存在 → 2」，与 `parse_pdf.py` 的实际分支对齐。

### 3.6 未修：`pages[].rotation` 不存在（不伪造）

`SKILL.md` §4.1 的 `pages[]` 字段里没有 `rotation`，引擎也没有写。所以本轮的旋转证据只用
**等价可观测量**：同一份单页 PDF 加 `/Rotate 90` 后，`pages[0].width/height` 从 `595×842`
变成 `842×595`（PyMuPDF 把 `/Rotate` 应用到了坐标系），并且 `char_recall=1.0`、首尾正文行
都还在。报告里如实写"未记录旋转"，而不是塞一个文档没声明的字段。若要做，属于 schema 变更
（要同步 `SKILL.md` 与 `references/schema.md`），不在本轮范围。

### 3.7 未修：无作者行的单页文档，编号标题会被 front-matter 吃成 `author`

旁支观察（不在 8 个 case 内）：如果第 1 页只有标题、没有作者/单位/摘要，
`extract_front_matter()` 会把 `1 INTRODUCTION` 切成 `INTRODUCTION` 当成作者名，
再按"包含作者名"把该块重标成 `author`，于是 `sections` 为空。

```
最小复现：单页，18 pt 标题 + 三栏各一个 14 pt 编号标题，无作者行/摘要
实测：    1 INTRODUCTION -> type="author"，sections=[]

原因：    NAME_RE 接受全大写单词；extract_front_matter() 末尾的
          `elif fm["authors"] and any(a in t ...): b["type"]="author"` 不区分 heading
候选修法：该分支加 `and b["type"] not in ("heading","title")`（1 行）

**试过并回退**：加了这一行后 `bert` 从 27 节变 **31 节**——这 4 个"新标题"里有一个其实是
附录里的项目符号列表（`- Effect of Number of Training Steps; and - Ablation for Different ...`），
说明作者规则此前恰好**掩盖**了一个误判标题。也就是说这 1 行不是净改善，反而让假标题多出来一个。
正确顺序是先加"项目符号不是标题"的规则，再放开作者分支；那需要完整的五篇重验。
本轮**回退**，代码里留了注释指向本节，不伪装成"已修"。
```

---

## 4. 改引擎后的回归（`work/regress.py`，五篇真实语料）

```
resnet       identical (583 blocks, 16 sections, recall 1.0018)
transformer  identical (510 blocks, 25 sections, recall 1.0012)
bert         identical (687 blocks, 27 sections, recall 0.9969)
gpt3         identical (961 blocks, 56 sections, recall 1.013)
vit          identical (742 blocks, 22 sections, recall 1.0016)

regress: OK - nothing moved
```

比对的键：`n_blocks / n_sections / n_headings / n_tables / n_figures / n_formulas /
char_recall / char_recall_vs_full_layer / dropped_running_chars / masked_figure_label_chars /
types / selfcheck.ok`。

`python tests/test_engine.py` 同时复跑：`27 checks, 0 failed`。

留在引擎里的改动有两处：`parse_pdf.py` 的**退出码/错误流**（§3.1、§3.2，不参与版面计算），
以及 `pdf_struct.py` 的**跨栏判据**（§3.3，只影响 `order` 与 `column`，不影响任何计数）。
两处改完五篇语料的报告**逐键相同**（含 `selfcheck.ok`），变的是块序与 overlay 上的序号。

---

## 5. 这份证据**不**证明什么

- 不证明三栏在**真实**期刊上的普适性：只是一个 3×60mm/6mm 的合成干净版面；
  倾斜扫描、跨栏公式、脚注穿插、栏内嵌图都没覆盖。SKILL.md §9 已声明"三栏及以上仍可能只判到 2 栏"，
  本轮证明了"干净三栏能判对栏数、不丢字、按栏读"，并修掉了它暴露的一个真实顺序缺陷（§3.3）。
- 不证明加密 PDF 能被**解密**：只证明"需要密码时会干净地退出 2"，不会尝试破解。
- 不证明 40% 截断的其它比例行为：只测了 40%（以及缺语料时的合成 6 页替代）。
- 不证明 OCR 识别率：本目录不涉及视觉模型（真实页的单次评测见 `results/ocr-eval.json`，n=1，且只到"上界"）。
