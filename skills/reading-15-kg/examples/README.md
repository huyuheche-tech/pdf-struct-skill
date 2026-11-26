# Example: two tiny papers, five nodes, four edges, three queries

> 本目录是**最小调用示例**，其中的输出标注为 EXAMPLE，**不是平台正式案例的结果**。
> 两篇论文都是自造的合成文本（p1 用 ResNet 设定，p2 用 ViT 设定），数据集不同。

## 输入

```
examples/
  case.json                 # output_contract: graph/queries/checks/metrics/status
  corpus-manifest.json      # 两篇：DOI、作者、source_hash、许可证
  material.json             # 索引：paper_id -> file
  primary-material.json     # p1，2 段（p1-1 方法、p1-2 结果）
  secondary-material.json   # p2，2 段（p2-1 方法、p2-2 结果）
  draft.json                # 5 节点 / 4 边 / 3 查询
```

## 运行

```bash
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out /tmp/ex --work /tmp/ex-work

python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out /tmp/ex --work /tmp/ex-work --draft examples/draft.json
```

## 检查了什么

- `n5 Top-1 accuracy` 跨两篇，`source_ids: ["p1","p2"]` + `merge_basis` → 合法合并；
- `e2`/`e4` 的 quote 分别在 `p1-2`、`p2-2` 里逐字命中 → `evidence_resolved = 4/4`；
- 没有把 76.8% 与 91.2% 合成一条 `outperforms`（数据集不同）；
- 3 条查询都取到了边 id + paragraph_id。

## 示例输出（EXAMPLE，不是正式评测结果）

```text
$ python scripts/run_case.py --case examples/case.json --input-dir examples \
      --out /tmp/ex --work /tmp/ex-work --draft examples/draft.json
case_id=example-kg status=success nodes=5 edges=4 queries=3 errors=0 warnings=0
```

`queries.md`：

```markdown
| id | 查询 | 命中节点 | 答案证据 | 状态 |
|---|---|---|---|---|
| q1 | Which dataset does ResNet-50 use? | n1 | edge@e1:p1-1; edge@e2:p1-2 | OK |
| q2 | What top-1 accuracy is reported for ViT-B/16? | n3,n5 | edge@e3:p2-1; edge@e4:p2-2 | OK |
| q3 | Which metric do both papers report? | - | edge@e2:p1-2; edge@e4:p2-2 | OK |
```

`result.json` 的 `main_result.metrics`：

```json
{"nodes": 5, "edges": 4, "evidence_resolved": 4,
 "merged": 1, "conflicts": 0, "queries": 3}
```

`graph.csv` 是两段式：

```csv
# section: nodes
id,name,type,source_ids,aliases,merge_basis
n1,ResNet-50,method,p1,ResNet50,
...
# section: edges
id,source,relation,target,source_id,paragraph_id,quote,conditions
e1,n1,uses,n2,p1,p1-1,train it on ImageNet-1k for 90 epochs,
```

> 说明：以上是**示例输出**，用来说明接口与校验形态；它不是平台正式案例的结果，
> 两篇论文也不是真实文献。
