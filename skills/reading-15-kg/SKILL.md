---
name: literature-knowledge-graph
description: 把两篇独立论文建成可回查的证据型文献知识图谱：节点/边逐条绑定 JATS paragraph_id 与原句，强制受控关系词表、同名合并依据、跨篇不合并数值结论；真实执行 ≥3 条查询并给证据，支持 --base 增量保留既有 id。当任务涉及"文献知识图谱/实体关系抽取/跨论文对比/图谱增量更新"时使用。
---

# 文献知识图谱：双论文证据绑定 + 查询执行 + 增量合并

## 0. 运行契约（先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，案例在 `/input/case.json` + `task.md`，成品写到 `/app/output/`。
两条命令可直接复制：

```bash
# 第 1 步：抽候选实体（不编造图谱），看材料与 paragraph_id 是否读对
python scripts/run_case.py --case /input/case.json --input-dir /input --out /app/output --work /app/work

# 第 2 步：把 nodes/edges/queries 写进 /app/work/draft.json，校验并出成品
python scripts/run_case.py --case /input/case.json --input-dir /input --out /app/output --work /app/work --draft /app/work/draft.json

# 增量：保留上次交付的节点 id，报 added / merged / conflicting
python scripts/run_case.py --case /input/case.json --input-dir /input --out /app/output --work /app/work --draft /app/work/draft.json --base /app/work/base-graph.json
```

`run_case.py` 会写：

| 文件 | 内容 |
|---|---|
| `graph.json` | `meta`（两篇论文的 DOI/许可证/source_hash/段落数）+ `nodes` + `edges` |
| `graph.csv` | 两段式 CSV：`# section: nodes` 与 `# section: edges` |
| `queries.md` | 每条查询的命中节点、答案证据（边 id + paragraph_id）、状态 |
| `checks.json` | `errors / warnings / conflicts / queries / incremental / summary` |
| `result.json` | 平台契约：`case_id` + `output_contract` 全部字段 + `status/evidence/uncertainty/sources` |

**draft.json 格式（只接受这一种）**

```json
{"nodes": [{"id": "n1", "name": "ResNet-50", "type": "method",
            "source_ids": ["p1"], "aliases": ["ResNet50"], "merge_basis": "",
            "evidence": [{"source_id": "p1", "paragraph_id": "p1-2",
                          "quote": "We use ResNet-50 as the backbone"}]}],
 "edges": [{"id": "e1", "source": "n2", "relation": "uses", "target": "n1",
            "source_id": "p1", "paragraph_id": "p1-2",
            "quote": "We use ResNet-50 as the backbone", "conditions": ""}],
 "queries": [{"q": "Which method outperforms ResNet-50 on ImageNet-1k?",
              "answer_ids": ["n2"]}]}
```

- `type` ∈ `method|dataset|metric|finding|material|task|author`
- `relation` ∈ `uses|compares|outperforms|supports|contradicts|part_of|measured_by`
- `paragraph_id` 是 **JATS 段落号**（`p1-3`），**不是 PDF 页码**；
- `quote` 必须能在该论文该段落里逐字找到（容空白/引号差异，不容改写）。

**预算**：64 次模型请求 / 900 秒 / 单回复 16384 token。建议每篇论文一次请求抽节点，
再一次请求连边与查询；每次只带当前论文的段落，不要一次塞两篇全文。

## 1. 用途与适用条件

把**两篇互相独立的论文**建成一张能逐条回查的图：每个节点说清"它从哪篇哪段来"，
每条边说清"依据哪句原文、在什么条件下成立"。查询不是装饰，必须真实执行并带证据。

适用：有段落级正文（JATS `paragraph_id` 的 JSON，或 md/txt）；两篇论文题目/数据/条件不同；
需要在已有图谱上增量加一篇新论文。
不适用：单篇论文的精读笔记（用 `structured-paper-notes`）；PDF 扫描件（先走文档解析拿文本）；
需要全文语义推理的综述生成（本 Skill 只保证结构化与证据，不判断结论对错）。

## 2. 硬约束（评分点 → 保证方式 → 失败 code）

| 评分点 | 本 Skill 怎么保证 | 失败时 |
|---|---|---|
| **每条都有证据** | 边必须有 `source_id` + `paragraph_id` + `quote`；quote 在对应论文段落里做逐字解析（`check_quote`）；节点也带 evidence | `evidence_unresolved` |
| **关系合法** | 受控词表 7 种；source/target 必须是已存在节点；禁止自环 | `relation_invalid` / `dangling_edge` / `self_loop` |
| **合并有依据** | 同名同类型多 id → `unmerged_duplicate`；同名不同类型 → 记 `name_conflict` 且必须保留两个；跨篇合并必须 `source_ids` 含两篇 | `unmerged_duplicate` / `name_conflict` / `merge_unsourced` |
| **跨篇不越界** | 两篇的数值结论文不得合成一条无 `conditions` 的 `outperforms/compares` 边 | `cross_paper_overreach` |
| **查询真实** | ≥3 条；逐条执行取节点/边 id + 证据；查不到必须写 `empty_reason` | `queries_thin` / `query_unevidenced` |
| **增量可复现** | `--base` 保留既有 node id，输出 `added/merged/conflicting`，合并必须给依据 | 冲突写进 `conflicting` + `incremental_conflict` 警告 |

**绝不允许**为了让检查变绿而删掉 `conditions`、把两篇的数字硬凑成一条边、或者把同名不同类的节点
合并成一个。这正是评委要看的失败模式。

## 2.9 题面四问对齐（评审核对用）

| 题面关注 | 本 Skill 的确定性保证 | 失败信号 | 不覆盖 |
|---|---|---|---|
| 抽得准 | 实体必须有 source_id + 原文短引 | `evidence_unresolved` | 实体是否穷尽 |
| 连得对 | 关系受控词表 + 方向 + 条件 | `relation_invalid` / `dangling_edge` | 关系强度 |
| 对得齐 | 合并必须有 `merge_basis`；同名不同类型不合并 | `unmerged_duplicate` / `name_conflict` / `merge_unsourced` | 语义消歧 |
| 查得到、回得去 | ≥3 条真实执行查询，结果带 id + 证据 | `queries_thin` / `query_unevidenced` | 查询语言通用性 |

### 2.10 交付自证字段（结果里直接读，不用自述）

`result.json` 顶层固定带三块**由实际运行算出来**的记录，供逐条复核：

| 字段 | 内容 | 对应题面要求 |
|---|---|---|
| `delivery_manifest` | `/app/output` 里真实写出的每个文件：文件名、字节数、sha256 前 16 位、是否可编辑 | 「结果可继续编辑」「可核验性」 |
| `change_record` | `modification_log`（本次改动台账及其来源字段）、`human_confirmation`、`material_gaps`、`anomalies` | 「版本与边界：修改差异、人工确认项、材料缺口和异常」 |
| `requirement_coverage` | 题面四个关注点逐条给 `satisfied`，命中的真实错误码放 `failed_checks`，只提示不判错的放 `advisory_checks`；`checks_watched` 列出每个码本次是 error / warning / 未触发 | 「完整性」「可核验性」 |

映射表在 `environment/requirements.json`（题面四问 → 引擎真实失败码），不是评委自评表。
例如跨篇数值结论没有条件时，「对得齐」会列出 `cross_paper_overreach`。

## 3. 操作流程

### 3.1 读输入，确认两篇是两篇

1. 读 `corpus-manifest.json`：每篇的 `paper_id / doi / authors / source_hash / license`。
   **两篇必须是独立论文**，不能是同一篇的正文+附录。
2. 读 `material.json`：它只是索引（`paper_id -> file`），正文在 `primary-material.json` /
   `secondary-material.json` 里。**按文件实际内容读，不要按文件名猜。**
3. 确认段落号是 `paragraph_id`（`p1-3`），不是 PDF 页码。混用页码会让所有证据失效。

### 3.2 先跑一遍候选抽取

```bash
python scripts/run_case.py --case /input/case.json --input-dir /input --out /app/output --work /app/work
```

输出 `graph.json` 里只有 `candidate: true` 的候选实体（`type` 为 `null`），`status=partial`。
它的作用是**确认材料读对了**（论文数、段落数、DOI），不是交付物。

### 3.3 建节点（模型做的事）

对每篇论文逐段抽：

- 方法（`method`）、数据集（`dataset`）、指标（`metric`）、结论（`finding`）、
  材料/样本（`material`）、任务（`task`）、作者（`author`）；
- 每个节点至少一条 evidence：`source_id` + `paragraph_id` + **原文短引**（3–25 词，能定位）；
- 别名放 `aliases`（`ResNet50` → `ResNet-50`），**不要**为别名另建节点。

### 3.4 连边（模型做的事）

每条边回答"谁对谁、在哪句、什么条件下"：

1. `relation` 只能取 7 种受控词；方向按字面（`n2 uses n1` 表示 n2 用了 n1）。
2. `quote` 必须来自 `source_id` 对应论文的 `paragraph_id`；
3. **同一篇内的比较**直接写；**跨篇比较**必须填 `conditions`（数据集、轮数、分辨率、评测口径），
   否则会被判 `cross_paper_overreach`；
4. 两篇的数值结论（如 76.8% vs 91.2%）**不能**合成一条 `outperforms`——它们不在同一数据集上。

### 3.5 合并与冲突

- 同名同类型只能有一个节点；合并后在 `merge_basis` 写依据（"same metric definition"）。
- 同名但类型不同（`ViT` 既是模型名又是数据集名）：**保留两个节点**，检查器会记 `name_conflict`，
  这不是让你合并的信号。
- 跨篇合并（一个节点来自两篇）：`source_ids` 必须同时含两篇，否则 `merge_unsourced`。

### 3.6 查询

至少 3 条，且要真的能查到：

1. 用图里的节点名/别名写问题；
2. `answer_ids` 填真实存在的节点或边 id；
3. 查不到就写 `empty_reason`（例如 "no edge in this corpus supports a cross-dataset claim"），
   不要硬凑一个答案；
4. 每条查询的证据来自答案节点相邻的**已解析**边；没有证据就是 `query_unevidenced`。

### 3.7 增量（`--base`）

`--base graph.json` 时：既有 id 一律保留；新节点若与既有节点同名同类型且有 `merge_basis` 则合并，
否则作为新节点加入并记 `conflicting`；id 撞车但实体不同时保留旧 id，新节点改用 `n3-b`。
输出三张清单：`added`（nodes/edges）、`merged`（from/into/basis）、`conflicting`（原因）。
**冲突是给人看的，不是自动消掉的**。

### 3.8 交付

`graph.json` 是机器可读的成品，`graph.csv` 方便人工抽查，`queries.md` 证明查询真的执行过。
`main_result.graph` 放整张图，`main_result.queries` 放执行结果，`metrics` 放计数。

## 4. warning 处置表

| warning | 含义 | 处置 |
|---|---|---|
| `orphan_node` | 节点没有任何边 | 补一条有证据的边，或确认它是独立实体并说明 |
| `node_unevidenced` | 节点只有 `source_ids`，没有原文短引 | 补 `evidence`（paragraph_id + quote） |
| `name_conflict`（无合并企图时） | 同名不同类型，已按规则保留两个 | 在 `merge_basis` 里写"为何不合并"，不要强行合并 |
| `unmerged_duplicate`（增量模式） | 同名同类型但无 `merge_basis`，已记为冲突 | 补依据后重跑；不要静默合并 |
| `incremental_conflict` | 新节点与既有 id 冲突，已改用 `-b` 后缀 | 人工确认后缀 id，更新下游引用 |

## 5. 异常处理

| 情况 | 动作 |
|---|---|
| 没有可读材料 | `status=failed`，`checks.errors=[{code:no_material}]`，不写假图谱 |
| 只有一篇论文 | `status=partial`，`uncertainty` 说明"题面要求两篇独立论文，当前只有一篇" |
| 段落没有 `paragraph_id` | 引擎按 `{paper_id}-{序号}` 生成，并在 `uncertainty` 标注"段落号是推断的" |
| 两篇其实是同一篇 | 停止建图，写 `uncertainty.human_review`，不要把同篇内容当跨篇证据 |
| quote 找不到 | 报 `evidence_unresolved`，**不要**改写 quote 去凑；回到原文重取 |
| 跨篇比较无 `conditions` | 报 `cross_paper_overreach`，补条件或改成 `compares` 并写明不可比 |
| 超出预算 | 先交已完成的节点/边（`status=partial`），`next_step` 写剩余段落号 |

## 6. 自检清单（提交前逐条打勾）

- [ ] `metrics.evidence_resolved == metrics.edges`（每条边都能解析）；
- [ ] 所有 `paragraph_id` 都是 `p{paper}-{n}` 形式，没有 PDF 页码；
- [ ] 每个跨篇节点 `source_ids` 含两篇，且有 `merge_basis`；
- [ ] 每条 `outperforms/compares` 跨篇边都有 `conditions`；
- [ ] ≥3 条查询，每条都有 evidence 或 `empty_reason`；
- [ ] `graph.csv` 两段齐全，行数与 `graph.json` 一致；
- [ ] `output_contract` 没有 `null`。

## 7. 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/run_case.py` | 运行入口（候选 / 校验 / 增量 / 写 result.json） |
| `scripts/kg_builder.py` | 材料装载、证据核验、合并策略、查询执行、增量合并、导出 |
| `scripts/skillkit.py` | 公共库（读文件、段落切分、quote 核验、契约回填），勿改 |
| `references/graph-schema.md` | 节点/边/查询字段契约与受控词表 |
| `references/merge-policy.md` | 同名、跨篇、增量合并的判定与依据要求 |
| `references/check-rules.md` | 每条检查的判据、误报边界、返修建议 |
| `examples/` | 最小调用示例（示例输出标 EXAMPLE） |
| `tests/cases/` | 3 个本地自测案例（**本地自测，不是平台正式案例**） |

## 8. 边界与诚实声明

- 本 Skill **不判断论文结论是否正确**，只保证"每个断言有出处、每条边有依据、每篇不串味"。
- 候选抽取（无 draft 时）只是词频启发式，`type` 为 `null`、标 `candidate: true`，**不是图谱**。
- 证据解析是**逐字匹配**（容空白与引号差异），改写过的 quote 会被判 `evidence_unresolved`；
  这是有意的严格。
- **不做**：PDF 版面还原、跨语言对齐、实体消歧的语义判断（只做名称归一 + 类型一致 + 依据字段）、
  综述写作。
- `tests/cases/` 里的 3 个案例是**本地自测，不是平台正式案例**：两篇合成论文（ResNet 类设定 p1 +
  ViT 类设定 p2，数据集/条件明确不同），材料全部自造，不能冒充评测结果。
