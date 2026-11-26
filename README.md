# weekly-skill — 科研 PDF 版面解析 Skill（阅读01｜文献文档解析）

一个**可直接安装、可被 Agent 调用**的 PDF 解析 Skill：把科研论文 PDF 变成"带页码与坐标的结构化文本"，
再拆成章节树、表格、图区、公式、参考文献，最后用一套自检把"提得全 / 排得对 / 拆得清 / 核得回"
变成可量化的数字，而不是口头承诺。

- 参赛题目：`product-arena-08-3027d350`（阅读01｜文献文档解析）
- **Skill 本体在 `outputs/`**（评测机的预检要求 `outputs/` 顶层有 `SKILL.md`）
- Skill 入口：`outputs/SKILL.md`（YAML frontmatter + 五步工作流）；**粘贴即用版**：`outputs/examples/quickstart.md`
- 实现：`outputs/scripts/`（PyMuPDF；无 OCR 二进制依赖，扫描件走"渲染页 + 视觉转录"分支）
- 方法说明：`outputs/references/method.md`；输出契约：`outputs/references/schema.md`；基线对照：`outputs/references/baseline.md`

## 1. 它解决什么

科研 PDF 解析的失败几乎总是同一批：双栏被读成"逐行交错"、标题粘进正文、表格单元格串行、
图注被当成正文、正文里混进页眉页脚与 arXiv 水印、扫描件直接没有文字层、字被提出来了但**不知道在第几页哪一块**。
本 Skill 对每一类都给出显式判据（而不是"用某个大模型试试"）：

| 失败类型 | 本实现的判据 |
|---|---|
| 双栏串行 | 短行投票求 gutter（`cov[x] <= 1`，容忍公式编号单点侵入），跨栏块作带区分界，带内分栏消费 |
| 标题粘正文 | `looks_like_heading_line()` 任一行像标题即断段 |
| 跨行标题变成假章节 | 同一页同字号、间距紧、无逗号的续行并回标题（`title_merged`）；标题不以连接词结尾（`heading_merged`） |
| 正文号字号的全大写小节漏判 | 编号 + 全大写 rest + 单行 + 无年份/无逗号 → `heading`（ICLR/NeurIPS 常见） |
| 表格串行 | 网格合理性闸门 + 用**词框**按行重建单元格（不依赖 `Table.extract()` 的 span 顺序） |
| 图注误判 | 图注必须与图区几何相邻（≤30pt 且水平重叠 ≥25%） |
| 页眉页脚混入 | 逐页字形/位置统计剔除，原文存 `dropped_running_text` 可复核 |
| 扫描件 | 退出码 3 + `ocr_pages.py` 渲染页与转录提示 + `merge_ocr.py` 合并，块标 `bbox:null`/`confidence` |
| 不可溯源 | 每块 `page` + `bbox` + `id`；`text.md` 每块带一行业主可读的 HTML 注释 |

## 2. 安装与最小调用

```bash
pip install pymupdf==2.1 pillow numpy          # 唯一必需依赖
python outputs/scripts/parse_pdf.py paper.pdf --out out/paper
```

产物：`doc.json`（结构化结果）、`text.md`（带溯源注释的阅读顺序文本）、`report.json`（精简报告）、
`tables/T*.csv`、`figures/F*.png`、`overlay/page-XX.png`（判版可视化：框色=类型，紫线=gutter，数字=阅读顺序）。

退出码：`0` 成功 / `2` 参数错误、文件打不开、加密、0 页 / `3` 无文本层（转 OCR 分支）或解析中途异常 / `4` 自检未通过。
完整说明见 `outputs/SKILL.md`，一屏接入版见 `outputs/examples/quickstart.md`。

## 3. 实测（可复现，非示例虚构）

命令与原始日志见 `results/run.log`，`results/<case>/` 保留了当时的产物：

| 文档 | 版面 | 页 | 块 | 章节 | 公式 | 表（可用/检出） | 图 | 参考文献 | `char_recall` | 自检 |
|---|---|---|---|---|---|---|---|---|---|---|
| arXiv 1706.03762 *Attention Is All You Need* | 单栏 | 15 | 510 | 25（26 标题） | 2 | 4 / 4 | 5/5 | 58 | 1.0012 | OK |
| arXiv 1512.03385 *ResNet*（CVPR 双栏） | 双栏（gutter 288–307pt） | 12 | 583 | 16 | 7 | 14 / 14 | 7/7 | 69 | 1.0018 | OK |
| arXiv 1810.04805 *BERT* | 双栏 | 16 | 687 | 27 | 2 | 6 / 7 | 4/4 | 115 | 0.9969 | OK |
| arXiv 2005.14165 *GPT-3*（75 页压力） | 单栏 | 75 | 961 | 56 | 0 | 48 / 51 | 33/33 | 183 | 1.0130 | OK |
| arXiv 2010.11929 *ViT*（**留出样本**） | 单栏正文 + 双栏附录 | 22 | 742 | 22 | 14 | 8 / 9 | 14/14 | 70 | 1.0016 | OK |

`char_recall = 输出正文字符 / (文本层字符 − 页眉页脚 − 图内/边角文字)`；> 1.05 视为重复输出（自检会报错）。对整层的原始比值另存为 `char_recall_vs_full_layer`，两者之差就是被显式排除的图内标签与页眉（逐块可查）。
ResNet 的 241 个 `figure_label` 块（图内坐标轴/结构标注）与 1 个 `margin_artifact` 不计入正文，
因此 `char_recall_vs_full_layer = 0.9674` —— 差额就是"本来就不该进正文"的部分，逐块可查。

**ViT 是定稿前才加入、未参与任何阈值调整的留出样本**：它一进来就暴露了两个泛化缺陷（两行标题被拆成假章节；
`3.1 VISION TRANSFORMER (VIT)` 这类"正文号字号 + 全大写"的小节标题未被识别），修复后 22 页 742 块、22 个章节全部正确，
修复动作写进 `warnings`（`title_merged` / `heading_merged`），可在 `results/vit/report.json`、`results/bert/report.json` 查到。
GPT-3 那例另有 3 条 `sparse_table` 非阻塞 warning（表头稀疏、仍可用），如实留在 `report.json`。

## 4. 为什么可信（自检 + 基线对照 + 证据链）

每次运行都会跑 4 条不变式，任一违反退出码 4：**每块可回页**、**页内顺序连续**、
**没有块跨越 gutter**、**`char_recall ≥ 0.90`**。

光有自检还不够，所以额外做了一件"对照组"的事：把**裸 Agent 最默认的写法**
（`"".join(page.get_text("text") for page in doc)`，官方纯文本路径，不人为削弱）与本引擎放在同一批 PDF 上逐项比：

| 判据（5 篇合计） | 裸 Agent | 本 Skill |
|---|---|---|
| 章节 / 表 / 单元格 | 0 / 0 / 0 | **146 / 80 / 2,586** |
| 可定位到页+坐标的块 | 0 | **3,483** |
| 图内文字混入正文 | 6,280 字符（`baseline` 口径；三工具口径 4,566） | **0**（引擎 `masked_figure_label_chars` 合计 6,638，逐块可查；ResNet p2 有 1 个 `x` 轴标漏遮罩，见 `outputs/response.md` §6） |
| 页眉页脚进正文 | 22 行 | **0**（归入 `dropped_running_text`） |
| 双栏串栏（读右栏又回左栏） | 48 次（三工具口径；`baseline` 口径 54） | **3**（resnet 1 / bert 2，从 `text.md` 实测；自检不变式为 0，两者不混用） |

同一批 PDF 还与 **`pymupdf4llm 2.1`**（PyMuPDF 官方 Markdown 导出器，最常见的轻量替代方案）做过同口径对比：

| 判据（5 篇合计） | 裸 dump | pymupdf4llm | 本 Skill |
|---|---|---|---|
| 章节 | 0 | 182（含把正文句判成标题） | **146**（有层级） |
| 表 | 0 | 86 | 85（另 5 张被闸门拒并记账） |
| 带坐标的块 | 0 | 0 | **3,483** |
| 图内文字混入 / 页眉行 | 4,566 / 22 | 4,447 / 22 | **0 / 0** |
| 双栏串栏 | 48 | 155 | **3** |
| 端到端耗时 | 0.3 s | 111.4 s | 132.6 s（纯文本模式 124.3 s） |

**不占"更快"**：比 `pymupdf4llm` 慢 10–19%，换来坐标、章节树、逐格 `bbox_cells` 与图内文字归位。原始数据：`results/compare_tools.json`、`results/perf.json`。

另有一组**不依赖语料**的自测：`python tests/test_engine.py`（27 条，三个合成 PDF）+ `python tests/test_robustness.py`（54 条，9 个坏输入与合成三栏页），共 **81 条断言**，不依赖 pytest、不联网。

复算：`python outputs/scripts/baseline_compare.py <paper>.pdf --doc out/<paper>/doc.json`；
原始数据 `results/baseline.json`，判据定义与逐例表 `outputs/references/baseline.md`。
字总数几乎不变（ResNet 49,574 → 47,956）——本 Skill 的价值不在多提字，而在**给每个字加上类型、顺序与坐标**。

## 5. 边界（如实声明，不猜）

- 三栏以上：合成三栏页已通过（`columns=3`、三个编号标题进 `sections`、`char_recall=1.0`），**真实期刊三/四栏未验证**；整页通栏插图夹在双栏之间时仍可能只判到 2 栏，需 overlay 复核。
- 无框线的"空白对齐表"不会被虚构成表格，会退回正文文本（`tables_rejected` 记录，五篇共 5 张）。
- 公式以**文本形式**给出，不做 LaTeX 重排；数学密集段落可能被标成 `formula`（文本不丢，只影响标签）。
- 扫描件没有矢量坐标：OCR 块只能定位到页，不能定位到框（`bbox: null`，并标 `confidence`）。
- 旋转水印统一进 `margin_artifact`，不参与阅读顺序。
- 连字符跨行、连字（ﬁ/ﬂ）**按原文保留**（"提得全"优先）；需要归一化时在消费端处理。
- `--pages 1-2` 探版模式会保留页眉（页眉判定依赖跨页重复），探版只看版面，正式解析请全量跑。

## 6. 目录

```
outputs/SKILL.md               Skill 本体：用途/调用/IO 契约/工作流/异常/自检/边界
outputs/scripts/pdf_struct.py  版面引擎（行重建、分栏、段落、分类、表格、图区、顺序、章节、元数据、自检）
outputs/scripts/parse_pdf.py   CLI：doc.json / text.md / report.json / tables / figures / overlay
outputs/scripts/baseline_compare.py  对照工具：裸 dump vs 本引擎的 6 项判据
outputs/scripts/compare_tools.py     三工具同口径对比（裸 dump / pymupdf4llm / 本引擎，7 判据）
outputs/scripts/perf_bench.py        逐篇耗时与峰值 RSS（3 次取中位数）
outputs/scripts/ocr_eval.py          扫描件评测：渲染 → 装转录 → 合并 → 与真值比对
outputs/scripts/ocr_pages.py   扫描件：渲染页 + 生成转录提示（供视觉模型使用）
outputs/scripts/merge_ocr.py   把逐页转录合并进 doc.json（保留 page 定位与置信度）
outputs/references/method.md   方法与阈值取舍（含每处阈值的失败模式）
outputs/references/schema.md   doc.json 字段级契约
outputs/references/baseline.md 基线对照的方法、逐例结果与读法
outputs/examples/quickstart.md 一屏粘贴即用（Agent 最短路径）
tests/test_engine.py           27 条黑盒断言（中文双栏 / 跨行标题 / 扫描件）
tests/test_robustness.py       54 条断言（0 字节/伪 PDF/截断/加密/0 页/单页/旋转/三栏/坏参数）
tests/fixtures/                三个合成语料 + outputs/scripts/make_fixtures.py 可重建
results/resnet/doc.sample.json 裁剪版 doc.json：sections + T1 的 cells/bbox_cells + 首页 blocks
outputs/examples/README.md     最小调用示例（明确标注为示例，非正式评测结果）
outputs/response.md            本次提交的主交付说明（结论/理由/实测/基线/边界/证据定位）
outputs/result.json            结构化结果（五例统计 + 汇总）
outputs/answer.txt             一句话结论 + 命令 + 关键数字
src/reproduce.py               ARM 入口：批量解析并跑自检（--pdf 可重复）
results/                       五例实测产物 + run.log + baseline.json（预检要求 ≤50 文件，现 37 个）
traces/trace.jsonl             归一化的 9 步 ARM 轨迹（工具配对、产物锚点、成本）
traces/raw_messages.jsonl      本次会话导出的模型对话记录
native_trace/session.jsonl     同一份对话记录（评测机要求 native_trace 下恰好一个文件）
characterization.json          与"理想解析"的偏差、失败模式、灵敏度（诚实记录）
arm_manifest.json              ARM v1.1 清单（入口、日志、产物、trace）
corpus/SOURCES.md              五篇语料的 arXiv 地址、字节数与 sha256（PDF 不随包分发）
LICENSE                        代码许可（MIT）
```

## 7. 环境与来源

- Python 3.13.12；PyMuPDF 2.1（MuPDF 1.28.6）；Pillow 12.3.0；numpy 2.5.1。CPU 即可，无 GPU。
- 演示语料为公开 arXiv 预印本（1512.03385、1706.03762、1810.04805、2005.14165、2010.11929），仅用于验证与示例；
  **PDF 未随包分发**，用 `corpus/SOURCES.md` 里的地址与 sha256 取回并校验（与 `doc.json.source.sha256` 对得上即同一份文件）。
- 无网络依赖、无外部 OCR 服务；全部逻辑在 `outputs/scripts/` 内可读、可改、可测。
- 代码许可见 `LICENSE`（MIT；PyMuPDF 为 AGPL 运行时依赖，未 vendoring）。
