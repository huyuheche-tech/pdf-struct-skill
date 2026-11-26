# 合并策略：什么时候能合并，什么时候必须分开

合并是知识图谱最容易出错的地方：合错了，两篇论文的数字就被缝成一条不存在的结论；
合少了，同一实体两条记录互相打架。这里给出可判定的规则，脚本按规则执行，不靠模型感觉。

## 1. 同名判定

节点的"名字集合" = `{name} ∪ aliases`，每个元素用 `skillkit.norm_key` 归一化
（小写、去标点、连字符与空格统一）。两个节点的名字集合有交集，就进入同一个候选簇。

例：`ResNet-50` 与 `ResNet50` 归一化后都是 `resnet 50` → 同簇。

## 2. 同簇之后怎么判

| 情况 | 判定 | code |
|---|---|---|
| 同类型、只剩 1 个 id | 正常 | — |
| 同类型、≥2 个 id | **必须合并成一个**，并写 `merge_basis` | `unmerged_duplicate`（error） |
| 不同类型、≥2 个 id | **必须保留两个**，记冲突 | `name_conflict` |
| 不同类型、且某个节点写了 `merge_basis` / `merged_from`（试图合并） | **报错** | `name_conflict`（error） |

`ViT` 既是模型名（`method`）又是数据集名（`dataset`）时，正确做法是两个节点，
在各自的 `aliases` 里说明，而不是合成一个 `type: "method|dataset"` 的四不像。

## 3. 跨篇合并

一个节点同时来自两篇论文（例如 `Top-1 accuracy` 在两篇里定义相同）时：

1. `source_ids` 必须**同时**包含两篇（`["p1","p2"]`）；
2. 必须有 `merge_basis`，写清为什么是同一实体：
   - 好："same metric definition (top-1 accuracy) reported by both papers"
   - 坏："same name"（同名不是依据，同名不同类型恰恰要分开）
3. 只写一篇的 `source_ids` 却声称跨篇 → `merge_unsourced`。

`merged_from: ["n1","n2"]` 形式的历史记录也检查：被引用的 id 必须存在，
其来源论文的并集必须被当前节点的 `source_ids` 覆盖。

## 4. 什么**不能**合并

- **不同数据集上的同名指标**可以合并"指标节点"（`metric`），但**不能**合并"数值结论"
  （`finding`）。76.8% 与 91.2% 是两个 finding，各自 `part_of` 自己的数据集。
- **同一缩写不同含义**（`ViT` 指模型 vs 数据集）→ 分开。
- **不同论文的 baseline**（`CNN baseline` vs `ResNet-50`）→ 分开，除非原文明确说同一个。

## 5. 跨篇数值结论（`cross_paper_overreach`）

判据：边的两个端点的来源论文并集 ≥2，`relation ∈ {outperforms, compares}`（或显式
`cross_paper: true`），`conditions` 为空，且 quote 只来自其中一篇 → 报错。

正确写法二选一：

1. 补 `conditions`：`"p1: ImageNet-1k; p2: CIFAR-100; different resolutions"`；
2. 不写这条边，改写成两条各自的 `measured_by`，再在 queries 里说明不可直接比较。

错误写法（会在测试里复现）：

```json
{"relation": "outperforms", "conditions": "",
 "quote": "91.2% top-1 accuracy on CIFAR-100"}   // 却连到 ImageNet-1k 的方法
```

## 6. 增量（`--base`）

| 情况 | 处理 | 记录 |
|---|---|---|
| 同 id、同 name、同 type | 保留 id，合并 aliases/source_ids/evidence | `merged`（basis 取 draft 的 merge_basis） |
| 同 id、不同实体 | 保留旧 id，新节点改 `n3-b`、`n3-b2`… | `conflicting`（id collision） |
| 不同 id、同 name+type、有 `merge_basis` | 并入旧节点 | `merged`（basis 原样记录） |
| 不同 id、同 name+type、无 `merge_basis` | 两个都留，记冲突 | `conflicting` + `incremental_conflict` |
| 其余 | 新增 | `added` |

**既有 id 一律不改**：下游引用（查询、报告、其他图）都靠它。
冲突进 `conflicting` 清单，由人决定是合并还是改名，脚本不替人决定。
