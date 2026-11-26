# 方法与实验字段契约

## draft.json

```json
{"methods": "方法与实验章节全文（Markdown 或纯文本）"}
```

```json
{"methods": "...",
 "params": [{"name": "optimizer.lr", "value": "0.001", "unit": "", "source": "config.json:5"}]}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `methods` | 是（或等价的 `text/body/content/raw`） | 正文；可含 `[TODO: ...]` 占位 |
| `params` | 否 | 补充台账；与材料冲突时正文数字仍按材料核验 |

## params.json

```json
{"n_params": 13,
 "params": [
   {"name": "optimizer.lr", "value": "0.001", "unit": "", "source": "config.json:4"}
 ]}
```

- `name`：摊平后的键（`a.b.c`、`list[0]`）。
- `value`：字符串，保留原写法。
- `unit`：能推断就写，推不出为空字符串。
- `source`：`文件名:行号`。

## gaps.json

```json
{"n_gaps": 2,
 "gaps": [
   {"code": "repro_gap", "item": "seed", "detail": "..."},
   {"code": "todo_placeholder", "detail": "[TODO: batch size]"}
 ],
 "repro_checklist": {"seed": false, "data_version": true, "split": true,
                     "batch_size": true, "learning_rate": true,
                     "epochs": true, "command": false, "env": true}}
```

- gap 默认不影响 `status`；正文声称 reproducible 时，缺失项会同时进 `checks.errors`。

## result.json（平台契约）

| 字段 | 说明 |
|---|---|
| `status` | `success` / `partial` / `failed` |
| `main_result.methods` | 方法正文 |
| `main_result.tables` | 参数台账（与 `params.json` 一致） |
| `main_result.checks` | `errors` / `warnings` / `gaps` / `summary` |
| `main_result.metrics` | `params / numbers_sourced / n_numbers / coverage / repro_items` |
| `output_contract` | 由 `skillkit.write_result` 按 case.json 回填 |
| `uncertainty.gaps` | 交付时必须交代的复现缺项 / TODO |

## 状态规则

- 没有任何可读材料 → `failed`。
- 没有 draft，或 draft 有硬错误 → `partial`。
- 有 draft 且 0 个硬错误 → `success`；`gaps` 不阻止 success。
