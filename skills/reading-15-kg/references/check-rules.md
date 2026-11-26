# 检查规则：判据、误报边界、返修建议

每条 `checks.json.errors/warnings` 都是 `{code, id, detail}`；`id` 是节点/边/查询 id，
便于直接定位到 `draft.json` 的那一行。

## 证据

| code | 级别 | 判据 | 误报边界 |
|---|---|---|---|
| `evidence_unresolved` | error | 边缺 `source_id`/`paragraph_id`/`quote` 任一；或 quote 在对应论文段落里找不到；节点没有任何 `source_ids`；节点 evidence 的 quote 找不到 | `check_quote` 容忍空白折叠、弯引号；**不容忍**改写、大小写以外的替换。段落号必须是该论文真实存在的 `paragraph_id` |
| `node_unevidenced` | warning | 节点只有 `source_ids`，没有 `evidence` | 候选节点（`candidate: true`）不报 |

解析顺序：`paper_id` → `paragraph_id` → 逐字匹配 quote。任何一步失败都指到具体原因
（`unknown paper` / `unknown paragraph_id` / `quote not found`）。

## 结构

| code | 级别 | 判据 |
|---|---|---|
| `relation_invalid` | error | `relation` 不在 7 种受控词里（大小写敏感，必须小写） |
| `dangling_edge` | error | `source` 或 `target` 不是已定义节点 |
| `self_loop` | error | `source == target` |
| `orphan_node` | warning | 节点没有任何边（候选节点除外） |

## 合并

| code | 级别 | 判据 | 说明 |
|---|---|---|---|
| `unmerged_duplicate` | error | 同簇、同类型、≥2 个 id | 合并并写 `merge_basis` |
| `name_conflict` | error/warning | 同簇、≥2 个类型 | 若无人试图合并 → warning（已正确保留两个）；若写了 `merge_basis`/`merged_from` → error |
| `merge_unsourced` | error | `merged_from` 引用不存在的 id；或跨篇合并的 `source_ids` 没覆盖两篇；或 `source_ids` ≥2 篇却没有 `merge_basis` | 见 `merge-policy.md` |

## 跨篇

| code | 级别 | 判据 |
|---|---|---|
| `cross_paper_overreach` | error | 两端点来源论文并集 ≥2，`relation` 是 `outperforms`/`compares`（或 `cross_paper: true`），`conditions` 为空，quote 只来自一篇 |

误报边界：`part_of`、`measured_by`、`uses`、`supports`、`contradicts` 不在此规则内——
它们不是"数值结论对比"。如果确实要写跨篇对比，补 `conditions` 即可。

## 查询

| code | 级别 | 判据 |
|---|---|---|
| `queries_thin` | error | 查询少于 3 条 |
| `query_unevidenced` | error | 答案 id 不在图里；或答案节点没有一条已解析的相邻边；或没有答案又没写 `empty_reason` |

"真实执行"的含义：脚本会记录 `matched_nodes`（按节点名/别名在问题文本里匹配）
和 `evidence`（实际取到的边 + paragraph_id + quote）。只有一个字符串问题、没有可解析证据的
查询不算执行过。

## 增量

| code | 级别 | 判据 |
|---|---|---|
| `incremental_conflict` | warning | `--base` 下出现 id 撞车，或同名同类型但无 `merge_basis` |
| `merge_unsourced` | error | 合并后节点的 `source_ids` 跨两篇但缺 `merge_basis` |

增量冲突是**给人看的**：脚本已经按规则保留旧 id 或新加 `-b` 后缀，
但最终该合并还是该改名，需要人确认。

## 返修顺序

1. 先修 `evidence_unresolved`——证据链断了，后面所有结论都不可信；
2. 再修 `dangling_edge` / `self_loop` / `relation_invalid`（结构性错误）；
3. 再处理 `unmerged_duplicate` / `name_conflict` / `merge_unsourced`（要想清楚再合并）；
4. 再补 `conditions` 消 `cross_paper_overreach`；
5. 最后补查询证据或 `empty_reason`。

任何一步都**不要**通过删边、删查询来消错：那会让图谱看起来干净，但丢掉了论文的实际结论。
