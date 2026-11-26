# 图谱字段契约

## 输入

```
/input/
  case.json                 # case_id、output_contract、可选 base_graph
  corpus-manifest.json      # 每篇：paper_id / doi / authors / source_hash / license / role
  material.json             # 索引：paper_id -> file，不含正文
  primary-material.json     # 正文：paragraphs[{paragraph_id, section, text}]
  secondary-material.json   # 正文
  draft.json                # 可选：模型产出的 nodes/edges/queries
```

`material.json` 只是索引。**正文只从 `paragraphs` 数组读**；md/txt 会被切成段落并编号
`{paper_id}-{n}`。混入 PDF 页码会让所有证据对不上。

## 节点

```json
{"id": "n1", "name": "ResNet-50", "type": "method",
 "aliases": ["ResNet50"], "source_ids": ["p1"], "merge_basis": "",
 "evidence": [{"source_id": "p1", "paragraph_id": "p1-2",
               "quote": "We use ResNet-50 as the backbone"}]}
```

| 字段 | 必需 | 说明 |
|---|---|---|
| `id` | 是 | 图内唯一，跨增量保持不变 |
| `name` | 是 | 规范名；别名放 `aliases`，不要另建节点 |
| `type` | 是 | 见下表；候选节点可为 `null`（`candidate: true`） |
| `source_ids` | 是 | 该实体出现的论文；跨篇合并要写全 |
| `aliases` | 否 | 用于同名判定（归一化后比较） |
| `merge_basis` | 合并时必需 | 一句话说明为什么是同一个实体 |
| `evidence` | 强烈建议 | `source_id` + `paragraph_id` + 原文短引 |
| `merged_from` | 增量时可选 | 被合并的旧 id 列表 |
| `candidate` | 否 | `true` 表示这是未定型的候选，不参与硬检查 |

### 节点类型

`method`（方法/模型）· `dataset`（数据集）· `metric`（指标）· `finding`（结论）·
`material`（材料/样本/数据划分）· `task`（任务）· `author`（作者/机构）

## 边

```json
{"id": "e4", "source": "n2", "relation": "outperforms", "target": "n1",
 "source_id": "p1", "paragraph_id": "p1-4",
 "quote": "which is 2.1 points above the ResNet-50 baseline",
 "conditions": "ImageNet-1k, 90 epochs, same training budget"}
```

| 字段 | 必需 | 说明 |
|---|---|---|
| `id` | 是 | 图内唯一 |
| `source` / `target` | 是 | 必须指向已存在节点；不得相同 |
| `relation` | 是 | 受控词表 7 种 |
| `source_id` | 是 | 证据来自哪篇论文 |
| `paragraph_id` | 是 | 证据来自哪一段（JATS 编号） |
| `quote` | 是 | 原文短引；逐字匹配 |
| `conditions` | 跨篇比较必需 | 数据集/轮数/分辨率/口径 |

### 关系词表

| relation | 方向 | 含义 |
|---|---|---|
| `uses` | A → B | A 使用了 B（方法用数据集、任务用方法） |
| `compares` | A ↔ B | A 与 B 被放在一起比较（**必须写 conditions**） |
| `outperforms` | A → B | A 在同一条件下优于 B（**必须写 conditions**） |
| `supports` | A → B | 证据 A 支持结论 B |
| `contradicts` | A → B | 证据 A 与结论 B 冲突 |
| `part_of` | A → B | A 是 B 的组成部分 |
| `measured_by` | A → B | A 的数值由 B 指标度量 |

方向按字面读：`n2 outperforms n1` 是 n2 更好。

## 查询

```json
{"q": "Which method outperforms ResNet-50 on ImageNet-1k?",
 "answer_ids": ["n2"], "empty_reason": ""}
```

- `answer_ids` 可以是节点 id 或边 id；
- 证据由脚本从答案节点的相邻**已解析**边里取（边答案直接取该边自己的证据）；
- 查不到时写 `empty_reason`，不要编一个答案。

## 输出 graph.json

```json
{"meta": {"case_id": "...", "mode": "draft|incremental|candidates",
          "papers": [{"paper_id": "p1", "doi": "...", "license": "...",
                      "source_hash": "...", "paragraphs": 6}],
          "paragraph_ids": "JATS paragraph_id, not PDF page numbers",
          "incremental": {"added": {...}, "merged": [...], "conflicting": [...]}},
 "nodes": [...], "edges": [...]}
```

`graph.csv` 是同一份数据的扁平化：第一段节点，第二段边，用空行与
`# section: nodes / # section: edges` 分隔，可直接用 Excel 打开。
