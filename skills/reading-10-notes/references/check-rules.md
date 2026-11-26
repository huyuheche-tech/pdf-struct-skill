# 检查规则：每个 code 的触发条件、误报边界与返修

> 硬错误计 0 才可能 `success`。不要为了消错删条目、删锚点或改引文原文。

## 1. 硬错误

| code | 触发条件 | 返修 |
|---|---|---|
| `field_missing` | 五字段缺失，或 `text` 为空；findings/limitations 不是列表 | 补字段与内容；缺失的字段**不要**用「无」占位 |
| `anchor_unresolved` | 锚点缺失、段号不存在、quote 为空、或 quote 不是该段连续子串 | 对照 `sections.json` 改段号；quote 从原文复制 |
| `findings_thin` | findings 少于 2 条 | 拆出第二条独立发现；不要把一句话拆成两句凑数 |
| `limitations_missing` | limitations 为空 | 从原文中找 limitation / future work / does not / 仅限 等表述 |
| `duplicate_point` | 两条 knowledge point 归一化相似度 > 0.90 | 合并为一条，或改写为不同层面（机制/边界/数据） |
| `section_uncovered` | 某个一级章节没有 `section_summaries` 条目 | 补该节摘要；摘要应概括该节作用，不是复述标题 |
| `summary_unanchored` | 某条 section summary 没有任何锚点 | 补一个该节的 anchor + quote |

## 2. 误报边界（这些情况仍算错误，但原因要写清楚）

- **quote 跨段**：一句话被段落边界切开时，`check_quote` 在原段内找不到，会报
  `anchor_unresolved`。修法是缩短 quote 到本段内的连续子串，而不是放宽校验。
- **同段落多字段引用**：允许；一个段落可以同时支撑 research_question 与 method。
- **findings 与 limitations 混写**：一条既有结论又有局限的句子，应拆成两条并各自锚定。
- **相似度 0.90 附近**：短句（<20 字）容易因为公共词过多而误判重复；此时应把两条
  改写成不同信息点，而不是改检查器阈值。
- **图表/公式里的结论**：若原文没有对应文字，不能凭图注臆造 quote；写进 `uncertainty`
  并留空，等人工补。

## 3. 不检查的东西（诚实边界）

- **摘要写得好不好**：引擎不判断概括质量，只看字段齐、锚点对、条数够。
- **发现是否真的成立**：引擎只验证「原文确实这么说」，不验证实验设计是否支持该结论。
- **局限是否完整**：只要求至少一条，不保证覆盖全部局限。
- **跨语言一致性**：中英混排时按字面匹配，不做翻译对齐。

## 4. 指标含义

| 指标 | 含义 |
|---|---|
| `sections` | 切出的章节数 |
| `covered` | 有一级章节摘要的章节数 |
| `fields_complete` | 五字段中完整且非空的个数（如 `5/5`） |
| `anchors_resolved` | 可解析锚点 / 全部锚点（如 `6/6`） |
| `duplicates` | 被判定重复的知识点条数 |

指标是**诊断**，不是分数；不要为了让 `duplicates` 变 0 而删掉真实知识点。
