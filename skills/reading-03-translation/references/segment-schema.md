# 数据契约

## plan.json

```json
{
  "source": "material.md",
  "target_language": "zh",
  "n_segments": 12,
  "zones": {"title": 1, "abstract": 1, "body": 9, "caption": 1},
  "glossary_size": 8,
  "glossary": [{"source": "attention", "target": "注意力", "note": ""}],
  "segments": [
    {"id": "p001", "zone": "title", "source": "...", "sentences": [{"id": "p001.s01", "text": "..."}],
     "locked_terms": [{"source": "attention", "target": "注意力"}],
     "numbers": ["12"], "citations": ["[3]"], "formulas": []}
  ]
}
```

## draft.json

```json
{"segments": [{"id": "p001", "target": "..."}],
 "back_translation": {"p001": "..."}}
```

- `id` 必须来自 `plan.json.segments[].id`；
- `target` 非空；
- `back_translation` 可选，只用于相似度提示。

## result.json（平台契约）

| 字段 | 类型 | 说明 |
|---|---|---|
| `case_id` | str | 来自 case.json 或材料文件名 |
| `status` | str | `success` / `partial` / `failed` |
| `main_result.translation` | str | `translation.md` 全文 |
| `main_result.segments[]` | list | `id/zone/source/target/ok` |
| `main_result.glossary` | list | 术语一致性矩阵 |
| `main_result.checks` | obj | `errors/warnings/summary` |
| `main_result.metrics` | obj | `segment_coverage/term_consistency/number_fidelity` |
| `output_contract` | obj | 按 `case.json.output_contract` 逐字段回填 |
| `output_contract_fields` | list | 契约要求的字段名 |
| `contract_unresolved` | list | 没能回填的字段（必须为空或说明） |
| `uncertainty` | obj | `warnings/human_review/missing_fields/note/next_step` |

`output_contract` 支持三种形态：字段名数组、`{"fields":[...]}`、`{字段: 描述}`。
无法识别的字段写 `null` 并进入 `contract_unresolved`，**不得猜测**。
