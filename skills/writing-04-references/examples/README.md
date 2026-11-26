# Example: 两条文献、正文引用顺序颠倒、按首次出现重编号

## 输入

- `examples/case.json`：契约 `references / renumber_map / checks / metrics / status`
- `examples/refs.bib`：2 条 BibTeX（都有 author/title/year/source/doi）
- `examples/manuscript.md`：先引 `[2]` 再引 `[1]`
- `examples/draft.json`：`merges: []`（无需合并）、`declared_complete` 两条都声明完整

```bash
# 只对账，不改写正文
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out --work ./work --check-only

# 完整流程：对账 + 重编号 + 出参考文献表
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out --work ./work --draft examples/draft.json
```

## 本例会校验什么

- 正文 `[2]`、`[1]` 都各自对上文献表里的一条（`missing=0`、`uncited=0`）；
- 按**正文首次出现**重编号：原 `[2]`(liu2021) → 新 `[1]`，原 `[1]`(chen2019) → 新 `[2]`；
- `renumber_map` 给出 old→new，正文按新号改写（`manuscript_renumbered.md`）；
- 4 位作者只列前 3 位 + `et al.`；
- GB/T 7714 顺序：`作者. 题名[J]. 刊名, 年, 卷(期): 起页-止页. DOI: ...`。

## 示意输出（EXAMPLE，不是平台正式结果）

`manuscript_renumbered.md`：

```
# Results

Sparse attention keeps the cost linear [1]. Attention helps in low-resource settings [2].
```

`bibliography.md`：

```
[1] Liu M, Ruiz A, Sun B, et al. Sparse attention for long documents[J]. Transactions on Natural Language Processing, 2021, 9(2): 112-130. DOI: 10.1000/tnlp.2021.112.

[2] Chen W, Zhao L. Attention improves sample efficiency[J]. Journal of Machine Learning Research, 2019, 20(4): 1-25. DOI: 10.1000/jmlr.2019.004.
```

`references.json` 里的 `renumber_map`：

```json
[{"old": 1, "key": "chen2019", "new": 2, "merged_into": null, "cited": true},
 {"old": 2, "key": "liu2021",  "new": 1, "merged_into": null, "cited": true}]
```

`metrics`：`{"entries": 2, "cited": 2, "uncited": 0, "missing": 0, "duplicates": 0, "field_completeness": 1.0}`

> 以上是**示意输出**，用来说明接口与校验形态；不是平台正式案例的结果，也不是评测分数。
