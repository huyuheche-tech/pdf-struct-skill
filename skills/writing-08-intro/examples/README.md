# Example: four sections bound to an evidence table

## Input

`examples/input/` contains `case.json`, `material.md`（摘要 + 结果 + 笔记）, `refs.bib`（5 条文献）和
`draft.json`（四段 + 3 条贡献绑定 + 2 组相关工作）。

```bash
python scripts/run_case.py --case examples/input/case.json --input-dir examples/input \
    --out /tmp/ex --work /tmp/ex-work --plan-only
python scripts/run_case.py --case examples/input/case.json --input-dir examples/input \
    --out /tmp/ex --work /tmp/ex-work --draft examples/input/draft.json
```

## What the binder checks

- 四段齐全（background / related_work / gap / contributions）；
- `18.4%` 能在 `evidence.json` 的 `p002.s03` 找到；
- 3 条贡献各有一条材料原句；
- gap 引了 2 篇不同文献；
- 相关工作 2 组，组内 key 都在 `refs.bib`；
- contributions 用 `author_judgment` 声明，不强行加引用。

## Illustrative output (EXAMPLE -- not an official case result)

`intro.md` 前几段（省略 groups 列表）：

```markdown
# EXAMPLE Attention Encoder for Low-Resource Text Classification

## Background
Label scarcity limits text classification in many applied domains [liu2019]. Prior systems rely on large annotated corpora, yet annotation remains expensive [zhang2020].

## Related Work
Attention-based encoders improve sequence modelling [vaswani2017]. Recurrent baselines remain competitive under low-resource settings [chen2021].

## Gap
Existing studies rarely isolate the encoder under a fixed budget [liu2019], and few report variance across random seeds [wang2018].

## Contributions
1. We introduce a lightweight attention encoder for low-resource text classification.
2. We show an 18.4% reduction in validation error on three datasets.
3. We evaluate every method under a fixed training budget.
```

`result.json` 的关键指标：

```json
{"status": "success",
 "metrics": {"n_claims": 1, "supported": 1, "contributions": 3,
             "bound": 3, "groups": 2, "citations": 6}}
```

> 说明：以上是**示例输出**，用来说明接口和校验形态；它不是平台正式案例的结果。
