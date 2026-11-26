# 科研 PDF 解析 Skill —— 提交说明（阅读01｜文献文档解析）

> 本题要求的是**一个可被 Agent 调用的 Skill**，而不是一次性答案。本文件说明 Skill 做了什么、凭什么可信、在哪些地方会失败。
> 文中所有数字都来自 `results/` 下可复现的运行记录；演示语料是五篇公开 arXiv 论文，**不是**隐藏评测用例，也不声称代表正式评测结果。
>
> 位置约定：Skill 本体在 `outputs/`（`outputs/SKILL.md` + `outputs/scripts/` + `outputs/references/` + `outputs/examples/`），
> 这是评测机预检的要求（`outputs/` 顶层必须有 `SKILL.md`）；`results/` 只放运行产物（预检要求 ≤50 个文件，现为 32 个）。

## 1. 一句话结论

`weekly-skill`（内部引擎名 `pdf-struct/2`）把「科研 PDF → 可核验结构化文本」做成一条可重复执行的流水线：
用 PyMuPDF 取字，按**短行投票**判分栏、按**带区（band）**定阅读顺序、按**词框**重建表格单元格、按**图注与图形邻接**确认图注归属，
每个输出块都带 `page` + `bbox` + 阅读序号，且用 4 条不变式在运行时自检；做不到的部分（扫描件、无框线表格）明确降级并标注，不猜。

**五篇 140 页合计**：3,483 个可回溯块、146 个章节、80 张表（2,586 个单元格，逐格带坐标）、495 条参考文献，自检全过。
与「裸 Agent 只做 `page.get_text()`」相比，同样的 PDF 上多得到 146 个章节、80 张表、3,483 个可定位块；
同一批 PDF 上与 `pymupdf4llm 2.1` 同口径对比（`results/compare_tools.json`），图内文字与页眉残留均为 **0**（两者分别是 4,447 / 4,566 字符与 22 / 22 行）。
本引擎自己记账的 `masked_figure_label_chars` 为 6,638，逐块可查（对照见 §5）。

## 2. 交付物

| 文件 | 作用 |
|---|---|
| `outputs/SKILL.md` | Skill 本体的契约：用途、调用方式、输入、输出字段、五步工作流、异常处理、自检清单、边界 |
| `outputs/scripts/pdf_struct.py` | 解析引擎（分栏、行合并、段落、分类、表格、图注、章节、元数据、参考文献、统计） |
| `outputs/scripts/parse_pdf.py` | 命令行入口：产出 `doc.json` / `text.md` / `report.json` / `tables/*.csv` / `figures/*.png` / `overlay/*.png` |
| `outputs/scripts/baseline_compare.py` | **对照工具**：同一份 PDF 上量化「裸 Agent 的纯文本 dump」与本引擎的差距（6 个判据） |
| `outputs/scripts/compare_tools.py` | **三工具同口径对比**：裸 dump / `pymupdf4llm` / 本引擎，7 个判据 × 5 篇，产出 `results/compare_tools.json` |
| `outputs/scripts/perf_bench.py` | 逐篇耗时（3 次取中位数）与峰值 RSS，产出 `results/perf.json` |
| `outputs/scripts/ocr_eval.py` | 扫描件评测：渲染 → 装转录 → 合并 → 与真值比对，产出 `results/ocr-eval.json` |
| `outputs/scripts/ocr_pages.py` | 扫描件分支：渲染页面 + 生成逐页转写提示词包（交给视觉模型转写） |
| `outputs/scripts/merge_ocr.py` | 把视觉转写结果合并回 `doc.json`，标注 `bbox:null` / `bbox_source:"vision"` / `confidence` |
| `outputs/examples/quickstart.md` | **粘贴即用**的一屏接入说明（Agent 读完就能正确调用，不需要读长文档） |
| `outputs/references/method.md` | 方法说明：每个阈值的取值理由、实测数据、已知失败模式 |
| `outputs/references/baseline.md` | 基线对照方法与逐例结果（本文件 §5 的完整版） |
| `outputs/references/schema.md` | 输出字段契约（逐字段类型与语义） |
| `tests/` | **81 条黑盒断言**：`test_engine.py` 27 条（3 个合成语料：中文双栏 / 跨行标题 / 扫描件）+ `test_robustness.py` 54 条（9 个坏输入 + 三栏），均不依赖 pytest、不联网 |
| `results/resnet/doc.sample.json` | 裁剪版 `doc.json`（12 页 `pages` + 16 节 `sections` + 首页 47 个 `blocks` + T1 的 63 个 `cells`/`bbox_cells`），让“逐格带坐标”可以直接翻看 |
| `corpus/SOURCES.md` / `LICENSE` | 五篇语料的 arXiv 地址与 sha256（PDF 不随包分发）/ MIT 许可 |
| `results/` | 五篇语料的运行产物 + `run.log` + `baseline.json` + `compare_tools.json` + `perf.json` + `ocr-eval.json` + `ocr/page-01.png` |
| `characterization.json` | 与论文/预期值的偏差、适用包络、失败模式、阈值敏感性 |
| `traces/trace.jsonl` | 构建过程的 9 步结构化轨迹（含工具调用配对、产物锚点、成本） |
| `raw_messages.jsonl` | 本会话的模型对话记录（Agent 轨迹） |

## 3. 方法与关键设计（为什么这样能"提得全 / 排得对 / 拆得清 / 核得回"）

1. **提得全**：文本层为唯一真值来源，不做 OCR 猜测；页眉/页脚/页码按「重复行的位置 + 内容相似度」判定后**丢弃但计数**，
   `stats.char_recall` = 实际输出字符 / （文本层字符 − 页眉页脚重复字符 − 图内/边角文字），五篇为 `1.0018 / 1.0012 / 0.9969 / 1.0130 / 1.0016`；对整层（什么都不扣）的比值另存为 `char_recall_vs_full_layer`（`0.9674 / 0.9660 / 0.9749 / 1.0121 / 0.9410`），差额就是刻意不放进正文的那部分。
   图内标签（坐标轴、图例）单独标为 `figure_label` 并计 `masked_chars`，**不混入正文**。
2. **排得对**：只用**短行**（宽度 < 0.62 内容宽）投票找栏间空白，容忍恰好 1 条越界行（公式编号 `(2)` 常见），最小沟宽 6 pt；
   两栏页若某页误判单栏，用全文模板回填（`cols_derived:"document_template"`）；
   阅读顺序按「通栏块把页面切成带区 → 带区内按栏左到右、栏内自上而下」，`order` 全局连续。
3. **拆得清**：段落合并要求「行距 ≤1.6 行高 + 水平重叠 ≥30% + 字号/字重一致 + 首行非缩进 + 上一行不是短行 + 上一行不是标题」；
   章节层级由编号与字号共同决定，`sections[].path` 用 ` / ` 连接父子路径；表格先用 `fill_rate≥0.40` 闸门拒绝"被误认为表格的正文框"，
   再按 `bbox_cells` 的**词框**重建每个单元格（这是修掉 `3 3××3 6 64` 这类串行错乱的关键）；
   公式区按数学符号密度与行数判定，上下标用 span 的 flag 位还原。
4. **核得回**：每个块都有 `page` 与 `bbox`；`text.md` 每块前带 `<!-- p3-b004 | type=body | col=0 | bbox=... -->` 溯源注释；
   `overlay/page-XX.png` 把块框、分栏沟、阅读序号画在原页上，人眼可一眼校验；`report.json` 记录 `selfcheck` 结果与各项统计。
5. **排得对（续）**：图/表块创建时 `column=-1`（未知），若它的 bbox 其实完全落在某一栏内，`order_blocks` 会按几何重新解析栏号；否则它会被当成“带区分界”抢到同带正文之前——ResNet 第 1 页的图 1 曾因此排在 `1. Introduction` 之前，修好后的顺序是“左栏到底 → 右栏图 1”，这正是双栏论文的读法。
6. **自检（运行时，失败即 exit 4）**：① 每块必须有 page+bbox；② 每页 order 连续无洞；③ 任何块不得跨栏沟；④ `char_recall ≥ 0.90`。

## 4. 实测（演示语料 + 一篇留出样本，可复现）

| 语料 | 版面 | 页 | 块 | 章节（标题） | 表（可用/检出） | 图 | 公式 | 参考文献 | `char_recall` | 自检 |
|---|---|---|---|---|---|---|---|---|---|---|
| `resnet.pdf` | 双栏 CVPR | 12 | 583 | 16（17） | 14 / 14 | 7/7 | 7 | 69 | 1.0018 | OK |
| `transformer.pdf` | 单栏 arXiv | 15 | 510 | 25（26） | 4 / 4 | 5/5 | 2 | 58 | 1.0012 | OK |
| `bert.pdf` | 双栏 ACL | 16 | 687 | 27（28） | 6 / 7 | 4 | 2 | 115 | 0.9969 | OK |
| `gpt3.pdf` | 单栏 75 页 | 75 | 961 | 56（57） | 48 / 51 | 33 | 0 | 183 | 1.0130 | OK |
| `vit.pdf` | 单栏正文 + 双栏附录（ICLR） | 22 | 742 | 22（23） | 8 / 9 | 14 | 14 | 70 | 1.0016 | OK |
| **合计** | — | **140** | **3,483** | **146** | **80 / 85** | **63** | **25** | **495** | — | **5/5** |

- 四篇是开发期语料；**`vit.pdf` 是留出样本**：定稿前最后加入、未参与任何阈值调整，加入后立刻暴露并修掉两个泛化缺陷
  （跨行标题被拆成假章节、`3.1 VISION TRANSFORMER (VIT)` 这类**正文号同字号的全大写编号小节**未被识别）。
  两处修复都写进了 `warnings`（`title_merged` / `heading_merged`），BERT 与 ViT 的 `report.json` 里可以查到。
- `bert.pdf` 的表 6/7 与 `gpt3.pdf` 的 48/51 差额是**被几何闸门拒绝**的网格（`tables_rejected`），不是漏检；拒绝后那块文字留在正文里，不漏字。
- `gpt3` 另有 3 条非阻塞 warning（`sparse_table:T35/T36/T44`），已点名在 `results/gpt3/report.json` 的 `selfcheck.warnings`。

- `146` 是 `sections` 数；另有 5 个**文档标题**块计入 `n_headings`（合计 151），标题不重复算作章节。
- `80 / 85` 与 `2,586` 是**通过几何闸门**的表与单元格；`report.json` 的 `n_table_cells` 统计的是**全部检出网格**（含 5 张被拒表，合计 2,904）。两个口径都真实，文档统一用前者，需要“检出量”时看 `stats.n_tables`。
- `vit.pdf` 的 `results/run.log` 里有 7 行 `MuPDF error: object is not a stream`（该 PDF 的部分流对象损坏，PyMuPDF 会跳过并继续）；解析结果与自检不受影响，但这是一个**未在早期版本披露**的降级信号，记在 §6。

复现命令：

```bash
python outputs/scripts/parse_pdf.py corpus/resnet.pdf --out out/resnet
python outputs/scripts/baseline_compare.py corpus/resnet.pdf --doc out/resnet/doc.json   # 与裸 dump 对照
# 或走 ARM 入口（批量 + 自检）
python src/reproduce.py --pdf corpus/resnet.pdf --pdf corpus/vit.pdf --out out --self-check
```

### 4.3 三工具同口径对比、性能与 OCR

| 判据（5 篇 140 页合计） | 裸 dump | pymupdf4llm 2.1 | 本 Skill |
|---|---|---|---|
| 章节 | 0 | 182（含把 `### greatly benefited from very deep models.` 这类正文句判成标题，且无父子层级） | **146**（`sections[].path` 有层级） |
| 表 | 0 | 86 | 85（另有 5 张被闸门拒，见 `tables_rejected`） |
| 带页 + 坐标的块 | 0 | 0 | **3,483** |
| 图内文字混入正文（字符） | 4,566 | 4,447 | **0** |
| 页眉行混入正文 | 22 | 22 | **0** |
| 双栏串栏（同口径实测） | 48 | 155 | **3**（resnet 1 / bert 2） |
| 端到端耗时 | 0.3 s | 111.4 s | 132.6 s（含出图与 overlay；`--no-overlay --no-figures` 为 124.3 s） |

- **不占"更快"**：比 `pymupdf4llm` 慢 10–19%，换来坐标、章节树、逐格 `bbox_cells` 与图内文字归位；纯文本模式只快 6%，说明时间花在版面分析而非出图。
- **表数量三家接近（85 / 86）**：`pymupdf4llm` 底层同样用 `find_tables`，这一项不算优势；差别在**单元格坐标**与**被拒表的显式记账**。
- **串栏是实测 3 次，不是 0**：旧 `baseline.json` 的 0 是"自检不变式"口径（禁止块跨 gutter，按构造成立），两者不混用；对外只用实测值。
- **OCR 单页上界**：resnet 第 1 页 200 dpi 渲染后由视觉模型转写、`merge_ocr` 合并——16 块全部 `bbox:null` / `bbox_source:"vision"` / `confidence` 非空，`char_recall:null`；折叠排版差异后字符一致率 1.0（未折叠 0.9956，差 9 个连字），n=1。**这是单页上界，不是识别率，也不是基准分。**

## 5. 相对"裸 Agent"的增益（可复算，不是形容词）

基线定义为 Agent 最默认的写法：`"".join(page.get_text("text") for page in doc)` —— 官方推荐的纯文本路径，**不人为削弱**。
六个判据全部由 PDF 几何独立计算，脚本 `baseline_compare.py` 可对任意 PDF 重跑，原始数据在 `results/baseline.json`。

| 判据 | 裸 Agent（5 篇合计） | 本 Skill | 说明 |
|---|---|---|---|
| 章节树 | 0 | **146** | 基线没有块类型，标题与正文不可分 |
| 表 / 单元格（带坐标） | 0 / 0 | **80 / 2,586** | 基线是文本流，行列与单元格归属不可恢复 |
| 可定位到页+坐标的块 | 0 | **3,483** | 基线只有字符，没有位置 |
| 图内文字混入正文 | 6,280 字符（`baseline.json` 口径；`compare_tools` 口径 4,566） | **0**（引擎 `masked_figure_label_chars` 合计 6,638） | 归入 `figure_label` 并计 `masked_chars`；ResNet p2 有 1 个 `x` 轴标因图区上沿偏 0.5pt 漏遮罩，已列在 §6 |
| 页眉页脚进正文 | 22 行（仅 ViT 触发） | **0** | 归入 `dropped_running_text`，逐页可查 |
| 双栏串栏（同一页读了右栏又回左栏） | 48 次（`compare_tools` 口径；`baseline` 口径 54） | **3**（resnet 1 / bert 2） | 从发出去的 `text.md` 实测；自检不变式为 0（按构造），两者不混用 |

三点必须说清楚，否则这张表就是吹牛：

1. **字符总数几乎一样**（resnet 49,574 → 47,956）。本 Skill 不比基线"多提字"，它给每个字加上**类型、顺序、坐标**，
   并把不该进正文的字**显式归位**而不是丢弃——差额能在 `masked_figure_label_chars` / `dropped_running_chars` 里逐项对上。
2. **`n/a` 就是 n/a**：单栏文档没有"串栏"，硬报数字才是造假；跨栏交错只在 resnet（12/12 双栏页）与 bert（16/16 双栏页）上统计。
3. **判据可被反驳**：换一个解析器只需替换 `doc.json`，判据不变；`baseline_compare.py` 的几何门槛（两栏各 ≥8 行、gutter ≤12% 内容宽）写在代码里，可复核。

## 6. 边界与已知限制（如实声明）

- **扫描件**：无文本层时 `parse_pdf.py` 以 exit 3 退出并提示走 OCR 分支；OCR 依赖视觉模型转写，此时 `char_recall` 为 `null`，**不得伪造**；块 `bbox` 为 `null`、`bbox_source:"vision"`，可核验性弱于文本层路径。
  已在真实页上跑通 1 次（resnet p1 @200dpi，`results/ocr-eval.json`）：**n=1、单模型、单次，且"扫描件"是 born-digital 页的干净光栅化**（无倾斜/噪点/复印模糊）——它是这条分支的上界，不是现场识别率。
- **≥3 栏**：合成三栏页已实测通过（`columns=3` / `column_template=3` / 3 个编号标题进 `sections` / `char_recall=1.0` / 栏序 0→1→2，见 `tests/robustness.md`），但**真实期刊的三栏/四栏尚未验证**；通栏图夹在双栏之间时仍建议用 `overlay/page-XX.png` 复核。
- **无框线表格**：`page.find_tables()` 找不到网格时不会虚构表格，正文按顺序输出（`tables_rejected` 显式记录，五篇共 5 张）。
- **数学密集段落**可能被标为 `formula`；**旋转水印**（如 arXiv 侧边章）可能被当作 `margin_artifact` 丢弃，字符记账里已计入 `masked/dropped`。
- 作者行顺序依赖 PDF 内文字流顺序，可能与视觉列顺序不完全一致（ResNet 上出现 `Xiangyu Zhang` 先于 `Kaiming He`）。
- **`--pages` 探版模式会保留页眉**：页眉判定依赖跨页重复，只解析 2 页时可能不足；探版只看栏数与版面，正式解析请全量跑。
- **遮罩按“块心是否落在图区矩形内”判定**：图区上沿判偏时，边缘轴标可能漏 1 处（ResNet p2 的 `x`），字符记账仍闭合，但“图内文字 0 混入”应读作“6,280 字符被归位，1 处漏网”。
- **扫描件的转录文件名曾是坏的**：`merge_ocr.py` 之前只找 `ocr/page-*.txt`，而文档让操作者写 `page-01.md`，照文档做必然 `exit 2`。本轮已修（两种扩展都接受），并由 `tests/fixtures/scanned.pdf` 端到端锁住；但**真实视觉模型的识别率仍未测**，只验证了“渲染 → 提示 → 合并”的管线。
- **坏输入是干净退出，不是 traceback**：0 字节 / 伪 PDF / 截断 / AES-256 加密 / 0 页统一 `exit 2`，`--pages 1-x` 也 `exit 2`，失败不留半成品 `doc.json`（9 个 case / 54 条断言，`tests/test_robustness.py`）。
- **图/表的栏号是按几何重算的**：跨栏图仍是带区分界；落入单栏的图表归该栏。若图区 bbox 本身判错（例如把图注算进图区），它会被分到错误的栏，需 overlay 复核。

## 7. 证据定位（供复核）

- 运行日志：`results/run.log`（五份语料的 `pages/blocks/headings/tables/figures/char_recall/selfcheck` 逐行记录）
- 统计与自检：`results/{resnet,transformer,bert,gpt3,vit}/report.json`
- 基线对照原始数据：`results/baseline.json`（逐例 + 逐页）；方法说明 `outputs/references/baseline.md`
- 带溯源注释的正文：`results/resnet/text.md`、`results/transformer/text.md`、`results/vit/text.md`
- 可视图层校验：`results/resnet/overlay/page-01.png`、`results/transformer/overlay/page-01.png`、`results/vit/overlay/page-01.png`
- 表格重建样例：`results/resnet/tables/T1.csv`
- 偏差与包络：`characterization.json`（7 条偏差、10 条包络（**8 实测 / 2 声明**）、6 条失败模式、4 条阈值敏感性、3 个合成语料 + 1 次真实页 OCR 上界）
- 自测：`tests/test_engine.py`（27 条，全绿）+ `tests/test_robustness.py`（54 条，全绿）；合成语料生成器 `outputs/scripts/make_fixtures.py`
- 三工具对比 / 性能 / OCR：`results/compare_tools.json`、`results/perf.json`、`results/ocr-eval.json`（均可由 `outputs/scripts/` 下同名脚本重算）
- 主产物样例：`results/resnet/doc.sample.json`（`sections` / `tables[].cells` / `bbox_cells` / `dropped_running_text` 都能直接看到）
- 接入方式：`outputs/examples/quickstart.md`（一屏，粘贴即用）

## 8. 运行状态

`成功`（五篇语料端到端解析，4 条不变式全过，含一篇未参与调参的留出样本；81 条自测断言全绿；9 个坏输入全部干净退出）。
对**未测版面**状态为 `部分完成`：真实期刊三/四栏、真实扫描件（倾斜/噪点）、>200 页——以 `characterization.json`
的 `envelope`（8 实测 / 2 声明）显式标注。不确定性集中在：分栏判定的边缘版面、表头与多行单元格的归属、
扫描件的字符还原率（只测到"干净光栅化的上界"，n=1）。
