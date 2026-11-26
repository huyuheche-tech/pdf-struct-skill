# 引言字段契约

## draft.json

```json
{
  "sections": {
    "background": "string",
    "related_work": "string",
    "gap": "string",
    "contributions": ["string", "string"]
  },
  "author_judgment": ["contributions"],
  "contribution_evidence": [
    {"contribution": 1, "anchor": "p002.s02", "quote": "逐字可解析的原句"}
  ],
  "groups": [
    {"label": "attention-based", "works": ["key1", "key2"]}
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `sections` | 是 | 四段；值可以是字符串，也可以是 `{"text": "...", "author_judgment": true}` |
| `author_judgment` | 否 | 声明"这段是作者判断、不需要引用"的段名列表 |
| `contribution_evidence[].contribution` | 是 | 1 起的序号，对应 `contributions` 顺序 |
| `contribution_evidence[].anchor` | 建议 | 取自 `evidence.json`；不在表里只记 warning |
| `contribution_evidence[].quote` | 是 | 必须能在材料里逐字找到 |
| `groups[].label` | 是 | 非空、具体 |
| `groups[].works` | 是 | 至少 1 个引用 key |

## evidence.json

```json
{"n_evidence": 7,
 "evidence": [
   {"anchor": "p002.s03", "text": "... 18.4% ...", "numbers": ["12", "18.4%", "0.001"]}
 ]}
```

- `anchor` 形如 `pNNN.sNN`：第 NNN 段第 NN 句，由材料按空行分段、按句号/问号/分号切句得到。
- 只有含数字、比较词或结论词的句子才进表。

## result.json（平台契约）

| 字段 | 说明 |
|---|---|
| `status` | `success` / `partial` / `failed` |
| `main_result.sections` | 四段成品文本 |
| `main_result.evidence` | 证据表 |
| `main_result.checks` | `errors` / `warnings` / `summary` |
| `main_result.metrics` | `n_claims / supported / contributions / bound / groups / citations` |
| `output_contract` | 由 `skillkit.write_result` 按 case.json 回填，未解析的字段会进 `contract_unresolved` |
| `uncertainty.next_step` | 没有 draft 时写明 draft 格式与命令 |

## 状态规则

- 没有可读材料 → `failed`。
- 没有 draft，或 draft 有硬错误 → `partial`。
- 有 draft 且 0 个硬错误 → `success`。warning 不影响状态。
