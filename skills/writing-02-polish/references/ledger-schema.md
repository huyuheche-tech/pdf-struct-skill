# 数据契约

## 1. plan.json（`--plan-only` 生成）

```json
{
 "source": "material.md",
 "n_sentences": 10,
 "glossary": [{"source": "attention model", "target": "attention mechanism", "note": ""}],
 "sentences": [
  {"id": "s01", "sentence": "Attention Improves Sample Efficiency ...",
   "locked_terms": [{"source": "attention model", "target": "attention mechanism"}],
   "numbers": ["12", "18.4%"], "citations": ["[3]"]}
 ],
 "instruction": "Write draft.json as {...}"
}
```

- 句号 `s01…sNN` 按段落切句后全局编号：标题、`Abstract.`、每个句末标点都算一句；
- `numbers` 已剥离 DOI/URL/引用标记，避免把 `10.1000/x` 当数据；
- `locked_terms` 只列"该句出现了术语表里的 source"，改稿里必须换成 target。

## 2. draft.json（模型写）

```json
{"edited": "改稿全文",
 "edits": [
   {"id": "s01", "original": "whether attention mechanism improves",
    "edited": "whether an attention mechanism improves",
    "type": "grammar", "reason": "缺少不定冠词"}
 ]}
```

| 字段 | 必填 | 约束 |
|---|---|---|
| `edited` | 是 | 改稿全文；段落结构与原文一致最利于对齐 |
| `edited_text` | 备选 | 只有全文时的别名（无台账） |
| `edits[].id` | 是 | 唯一；建议 `s01…`，允许与句号不同 |
| `edits[].original` | 是 | **必须是原文中真实存在的片段**，可长可短 |
| `edits[].edited` | 是 | 改后片段，必须能在改稿中找到 |
| `edits[].type` | 是 | `grammar` / `term` / `tone` / `clarity` |
| `edits[].reason` | 是 | 一句话说明改动的理由；空字符串等同缺失 |

## 3. edits.json（引擎写）

```json
{
 "edits": [
  {"id": "s01", "original": "...", "edited": "...", "type": "grammar",
   "reason": "...", "source": "ledger", "anchored": true,
   "change_type": "grammar", "sentence": "s03"}
 ],
 "summary": {"edit_count": 4, "ledger": 4, "auto": 0, "unexplained": 0,
             "by_type": {"grammar": 2, "term": 2, "tone": 0, "clarity": 0}}
}
```

- `source=ledger`：来自 draft；`source=auto`：引擎按句对齐补的（无 reason → 必报 `edit_unexplained`）；
- `sentence`：该条对应 `plan.json` 的句号，便于回查。

## 4. checks.json

```json
{
 "errors": [{"code": "number_changed", "id": "s04", "detail": "number replaced: 18.4% -> 18.0%"}],
 "warnings": [{"code": "hedge_weakened", "id": "s07", "detail": "..."}],
 "sentences": [{"id": "s04", "op": "replace", "change_type": "term",
                "source": "...", "edited": "...", "issues": ["number_missing"]}],
 "summary": {"n_sentences": 10, "n_edited_sentences": 10, "n_errors": 1, "n_warnings": 0}
}
```

`op` 取值：`equal / replace / delete / insert`；`change_type` 取值：
`grammar / term / tone / clarity / unchanged / deleted / inserted`。

## 5. result.json（平台契约）

| 字段 | 类型 | 说明 |
|---|---|---|
| `case_id` | str | 来自 `case.json` 或材料文件名 |
| `status` | str | `success` / `partial` / `failed` |
| `main_result.edited_text` | str | 改稿纯文本（**不含**台账表） |
| `main_result.edits[]` | list | 同 `edits.json.edits` |
| `main_result.checks` | obj | `errors/warnings/sentences/summary` |
| `main_result.metrics` | obj | `edit_count/unexplained/number_drift/hedge_drift/residual_grammar` |
| `main_result.files` | obj | 四个产物的文件名 |
| `output_contract` | obj | 按 `case.json.output_contract` 回填 |
| `output_contract_fields` | list | 契约要求的字段名 |
| `contract_unresolved` | list | 没能回填的字段（必须为空或说明） |

`output_contract` 支持三种形态：字段名数组、`{"fields":[...]}`、`{字段: 描述}`。
无法识别的字段写 `null` 并进入 `contract_unresolved`，**不得猜测**。

## 6. status 判定

| 情形 | status |
|---|---|
| 没有可读材料（troff/pdf 抽不出文本） | `failed` |
| 没有 draft，或 draft 里没有改稿全文 | `partial`（写 `uncertainty.next_step`） |
| 有 draft 且 `errors` 为空 | `success` |
| 有 draft 但有 error | `partial` |

**绝不把没做的事写成 success**：只有一条 reason 缺失也仍然是 `partial`。
