# 基线对照：裸 Agent 的默认输出 vs 本 Skill

> 目的：把"比裸 Agent 好"从主观判断变成**可复算的数字**。
> 数据文件：`results/baseline.json`（逐例、逐页都有记录）。复算命令：

```bash
python scripts/parse_pdf.py corpus/resnet.pdf --out out/resnet
python scripts/baseline_compare.py corpus/resnet.pdf --doc out/resnet/doc.json
```

## 1. 基线怎么定义（不设稻草人）

基线 = 一个不会解析版面的 Agent 用 PyMuPDF 最默认的写法取文本：

```python
text = "".join(page.get_text("text") for page in fitz.open(pdf))
```

这是**官方推荐的纯文本抽取路径**，不是我们人为削弱的版本：它保留了全部字符，
只是没有块类型、没有坐标、没有表格网格、没有阅读顺序修正。它恰好是"裸 Agent 能拿到的最好结果"。

## 2. 判据（每条都能被第三方独立复算）

| 判据 | 定义 | 为什么重要 |
|---|---|---|
| `running_header_lines` | 被本引擎判定为页眉/页脚而丢弃的行，在基线文本里仍出现的行数 | 页眉页脚进正文会污染摘要与检索 |
| `figure_label_chars_in_body` | 图内文字（坐标轴、图例）的字符数，基线里它们混在正文中 | 图内标签当正文会让"这一段讲了什么"答错 |
| `headings_glued_into_prose` | 本引擎的标题块，在基线文本里被并进长句（不再是独立行）的个数 | 标题粘进正文 → 章节树无法还原 |
| `cross_column_interleavings` | 双栏页上"读完右栏又回到左栏"的次数（几何判定：两栏各 ≥8 行、gutter ≤12% 内容宽） | 这是"串栏"的直接计数，不是观感 |
| `tables / table_cells` | 基线：0 / 0（纯文本没有网格）；本引擎：`n_rows × n_cols` 之和 | 表格行列与单元格归属是本题"拆得清"的核心 |
| `blocks_with_bbox` | 能回到原页坐标的块数 | 没有坐标就无法"核得回" |

## 3. 实测（与 `results/*/report.json` 同一次运行）

| 语料 | 页 | 页眉行残留 | 图内文字混入（字符） | 标题粘连 | 跨栏交错 | 表 / 单元格 | 有坐标的块 | 章节 |
|---|---|---|---|---|---|---|---|---|
| resnet.pdf（CVPR 双栏） | 12 | 0 → 0 | 1653 → **0** | 0 → 0 | 32 → **0** | 0/0 → **14/213** | 0 → **583** | 0 → **16** |
| transformer.pdf（arXiv 单栏） | 15 | 0 → 0 | 1122 → **0** | 0 → 0 | n/a | 0/0 → **4/70** | 0 → **510** | 0 → **25** |
| bert.pdf（ACL 双栏） | 16 | 0 → 0 | 1140 → **0** | 2 → **0** | 22 → **0** | 0/0 → **6/183** | 0 → **687** | 0 → **27** |
| gpt3.pdf（75 页长文） | 75 | 0 → 0 | 0 → 0 | 0 → 0 | n/a | 0/0 → **48/1843** | 0 → **961** | 0 → **56** |
| vit.pdf（ICLR 模板，未见样本） | 22 | 22 → **0** | 2365 → **0** | 0 → 0 | n/a | 0/0 → **8/277** | 0 → **742** | 0 → **22** |
| **合计** | 140 | **22** | **6280** | **2** | **54** | **80 / 2586** | **3483** | **146** |

"→"左边是基线，右边是本 Skill。加粗表示差异来自结构化处理，而不是字符数变化。

## 4. 怎么读这张表（避免过度解读）

- **字符总数几乎一样**（如 resnet 49574 vs 47956，差值是图内文字与页眉页脚被归位而非丢弃）。
  本 Skill 的价值不在"多提字"，而在**给每个字加上类型、顺序和坐标**，并把不该进正文的字**显式归档**（`figure_label` / `margin_artifact` / `dropped_running_text`），可逐块核对。
- **`n/a` 是真的不适用**：单栏文档没有"串栏"这回事，硬报一个数字才是造假。跨栏交错只在 resnet（12/12 双栏页）与 bert（16/16 双栏页）上统计。
- **`running_header_lines` 只在 ICLR 模板上非零**：CVPR/arXiv/ACL 这三篇的页眉只有页码，本引擎与基线都不把它算作正文；vit 每页有 `Published as a conference paper at ICLR 2021`，基线 22 行全部保留，本引擎 0 行并计 `dropped_running_chars = 849`。
- **`figure_label_chars` 是"少提了字"的地方**，但这是有意为之：它们在图内，不属于正文；`doc.json` 里仍以 `type=figure_label` 保留，`masked_chars` 记账，`char_recall_vs_full_layer` 因此小于 1（resnet 0.9674、vit 0.9410）。想连图内文字一起要，把这两类块取出来即可。
- gpt3 的 `figure_label_chars = 0` 不是"更好"，而是该文档没有需要遮蔽的图内文字（图都是位图，不含文本层）。

## 5. 复算一致性

`baseline_compare.py` 只用两个输入：PDF 本身，以及本引擎产出的 `doc.json`（提供 gutter 几何、页眉清单、块清单）。
换实现只需替换 `doc.json`，判据不变；因此这张表可以被任何人用同一批公开 PDF 复现或反驳。
