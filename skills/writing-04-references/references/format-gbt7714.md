# GB/T 7714—2015 拼接规则与 TODO 约定

本 Skill 只输出**文本形态**的顺序编码制参考文献表，不做 Word 域、不做悬挂缩进。
每条的字段顺序固定，缺字段就地替换成 `[TODO: 字段名]`，**不改变其余顺序**。

## 1. 各类型模板

| 类型 | 模板 | 必填（缺则 TODO） |
|---|---|---|
| `J` 期刊 | `作者. 题名[J]. 刊名, 年, 卷(期): 起页-止页. DOI: ...` | author / title / year / journal / volume / pages |
| `C` 会议 | `作者. 题名[C]//论文集名. 年: 起页-止页. DOI: ...` | author / title / year / booktitle / pages |
| `M` 专著 | `作者. 题名[M]. 出版地: 出版者, 年. DOI: ...` | author / title / year / publisher |
| `D` 学位论文 | `作者. 题名[D]. 保存地: 保存单位, 年. DOI: ...` | author / title / year / school |
| `EB` 电子资源 | `作者. 题名[EB/OL]. 网址, 年. DOI: ...` | author / title / year / url |

固定附加：`doi` 缺失时在该条末尾追加 `[TODO: doi]`（不编 DOI）。
`issue`（期）是**可选**字段：没有就不写括号，例如 `2019, 20: 1-25`。

## 2. 作者

- 3 位及以内全列，用 `, ` 分隔：`Chen W, Zhao L`；
- 超过 3 位，列前 3 位 + `等`（中文姓名）或 `et al.`（西文姓名）；
- 西文姓名转 `姓 名首字母`：`Wei Chen` → `Chen W`，`Wei R. Chen` → `Chen W R`；
- 已是 `Chen W` 形式的**原样保留**，不二次转换（否则会变成 `W C`）；
- 中文姓名原样保留（`张三`）。

判据：名字里出现汉字即按中文处理（`等`）；否则按西文处理（`et al.`）。
混合团队（中英作者混排）取"含汉字即有中文作者"，用 `等`。

## 3. 题名与标识

- 题名原样保留大小写，不擅自改斜体/句首大写；
- 题名后紧跟 `[J]` `[C]` `[M]` `[D]` `[EB/OL]`，由 `@article` / `@inproceedings` / `@book` /
  `@phdthesis` / `@misc` 等映射得到；
- 会议文献用 `[C]//论文集名` 的双斜线形式。

## 4. 页码与卷期

- 页码统一用半角连字符：`45--67` → `45-67`，`45–67` → `45-67`；
- 单页（`45`）原样保留；
- 卷期写作 `卷(期)`：`20(4)`；只有卷时写 `20`；只有期时 `(4)`。

## 5. TODO 约定（不许编造）

| 情况 | 输出 | 同时 |
|---|---|---|
| 缺 DOI | `... 1-25. [TODO: doi].` | `completeness.doi=false`，`field_missing`（warning） |
| 缺卷 | `... 2019, [TODO: volume](4): 1-25.` | `completeness` 里 author/title/year/source 仍可为 true |
| 缺页 | `... 2019, 20(4): [TODO: pages].` | 同上 |
| 缺刊名 | `... [J]. [TODO: journal], 2019, ...` | `completeness.source=false` |
| 缺作者 | `[TODO: author]. 题名[J]. ...` | `completeness.author=false` |
| 缺年 | `... 刊名, [TODO: year], 20(4): 1-25.` | `completeness.year=false` |

`completeness` 的五个布尔项就是 `author/title/year/source/doi`，与上表一一对应。
`complete = all(五項)`；`metrics.field_completeness = 完整条目数 / 条目总数`。

## 6. APA 7（`--style apa`）差异

`作者 (年). 题名. 刊名, 卷(期), 起页-止页. https://doi.org/xxx`

- 作者写 `Chen, W., & Zhao, L.`（姓, 名首字母.，最后一位前加 `&`）；
- 年加圆括号，题名后是句点而不是 `[J]`；
- DOI 写成 `https://doi.org/` 全链接；缺失时不追加 TODO（APA 允许无 DOI），
  但 `completeness.doi` 仍为 false，`field_missing` 仍会报 warning。

## 7. 编号

- 参考文献表按**正文首次出现**编号，从 1 开始连续；
- 未引条目排在其后，编号继续增长（不删除、不留空号）；
- 正文里的数字标记同步改写；同一括号内多个编号升序、去重，连续 ≥3 个压成 `a-b`。
