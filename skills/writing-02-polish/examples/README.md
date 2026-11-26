# Example: 一段英文，一处语法改动，数字/引用/hedge 全部保留

## 输入

- `examples/case.json`：契约 `edited_text / edits / checks / metrics / status`
- `examples/material.md`：标题 + 一段（3 句）
- `examples/draft.json`：改稿全文 + 1 条台账

```bash
# 计划
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out --work ./work --plan-only

# 校验 + 出成品
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out --work ./work --draft examples/draft.json
```

## 本例会校验什么

- `a expensive` → `an expensive`，且只有这一条改动（`edit_count == 1`）；
- `16 GB`、`4096`、`62.5%` 三个数字逐字保留；
- `[5]` 还在原位；
- `may need` 仍是 `may need`（没有升级成 `demonstrates`）；
- 改稿里没有残留的 a/an、双空格、`et al` 缺句点。

## 示意输出（EXAMPLE，不是平台正式结果）

`result.json`：

```json
{
 "case_id": "example-polish-001",
 "status": "success",
 "main_result": {
  "edited_text": "Sparse Attention for Long Documents\n\nDense attention is an expensive baseline for long inputs: a 4096-token sequence may need 16 GB of memory [5]. Sparse attention reduces this by 62.5% in our runs.",
  "edits": [{"id": "e01", "original": "is a expensive baseline",
             "edited": "is an expensive baseline", "type": "grammar",
             "reason": "元音音素前用 an", "source": "ledger", "change_type": "grammar"}],
  "metrics": {"edit_count": 1, "unexplained": 0, "number_drift": 0,
              "hedge_drift": 0, "residual_grammar": 0}
 },
 "output_contract": {"edited_text": "...", "edits": ["..."], "checks": {...},
                     "metrics": {...}, "status": "success"},
 "contract_unresolved": []
}
```

`polished.md`：

| ID | 类型 | 原文 | 改后 | 理由 |
|---|---|---|---|---|
| e01 | grammar | is a expensive baseline | is an expensive baseline | 元音音素前用 an |

> 以上是**示意输出**，用来说明接口与校验形态；不是平台正式案例的结果，也不是评测分数。
