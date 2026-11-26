# 输入与输出契约

## 输入

```
/input/
  case.json            # 必需：case_id、output_contract、可选 main_tex / compile
  main.tex             # 主文件（有 \documentclass）
  refs.bib             # 可选，可多个
  draft.tex            # 可选：模型/人修好的版本（--draft 指向它）
```

`case.json` 支持的字段：

| 字段 | 作用 |
|---|---|
| `case_id` | 结果里的 `case_id`，缺省用主文件名 |
| `main_tex` / `main` / `tex` / `source` | 指定主文件（相对 `/input`） |
| `compile` | `false` 时不做编译（本地案例用它保证离线可复现） |
| `output_contract` | 需要回填到 `result.json.output_contract` 的字段名，可为 list 或 `{fields:[...]}` |

没有 `output_contract` 时脚本照常产出，只是 `output_contract` 为空对象；
**有 `output_contract` 时不能出现 `null`**——脚本会在启动时检查，缺字段写进 `contract_unresolved`。

## draft

`--draft` 指向一个 `.tex` 文件，是**模型修好后的完整主文件**（不是 diff）。
它被当作新的分析源：`diagnostics` 反映 draft 的状态，`main_result.latex` 就是 draft（或它的 fixed 版）。

没有 `--draft` 时：

- 全部产物照写（方便先看问题）；
- `status=partial`；
- `uncertainty.next_step` 写明"存成 /app/work/draft.tex 后重跑"。

## 输出

| 文件 | 读者 | 要点 |
|---|---|---|
| `result.json` | 平台 | `case_id`、`status`、`output_contract`、`main_result`、`evidence`、`uncertainty`、`sources` |
| `report.md` | 人 | 每条诊断 `file:line` + 原行 + 修复建议；编译结果；patch plan |
| `diagnostics.json` | 工具 | `errors / warnings / fixes / patch_plan / compile / pre_fix` |
| `checks.json` | 工具 | `errors / warnings / summary`（summary 含 `compiled`、`compiler_missing`） |
| `fixed.tex` | 人 | 仅 `--fix`；只含两类安全修复 |

`result.json.main_result.metrics`：

```json
{"errors": 2, "warnings": 3, "compiled": false,
 "cite_keys": 3, "labels": 4, "lines": 61}
```

- `cite_keys`：正文里出现过的**不同** key 数（含 `TODO-`）；
- `labels`：不同 `\label` 数；
- `compiled`：**只有在真实两遍编译成功后才为 true**。

## 状态

| 条件 | status |
|---|---|
| 没有可读 `.tex` | `failed` |
| 没有 `--draft` | `partial` |
| 有 draft，0 error | `success` |
| 有 draft，≥1 error | `partial` |

warning 不影响 status；但 `caption_missing` / `bib_unused` 这类在投稿前应清零，
脚本会把它们放进 `uncertainty.human_review`。
