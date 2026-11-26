# 数据契约：draft.json / nanopub.json / result.json

## 1. draft.json（模型写，唯一入口）

```json
{"assertions": [
  {"id": "a1",
   "text": "The calibration layer reduces expected calibration error from 8.4% to 6.3% on ImageNet.",
   "subject": "calibration layer",
   "predicate": "has_property",
   "object": "expected calibration error 6.3%",
   "conditions": "",
   "evidence": "On ImageNet, the calibration layer reduces expected calibration error from 8.4% to 6.3%.",
   "source_id": "paper-imagenet-calibration",
   "paragraph_id": "s02.p01",
   "confidence": "high"}
]}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 断言编号，稳定不变；导出 URI 由 `text+source_id` 决定，不依赖 id |
| `text` | 是 | 单一可判定的断言句；一个主语 + 一个谓语 + 一个宾语 |
| `subject` / `predicate` / `object` | 是 | 三元组；`predicate` 必须来自受控词表（见 `controlled-vocab.md`） |
| `conditions` | 条件句必填 | 原文的 under / when / only if / 在…条件下 等限定 |
| `evidence` | 是 | 原文短引，≤400 字符，必须是所引段落的连续子串 |
| `source_id` | 是 | 论文/来源标识；同一篇内保持一致 |
| `paragraph_id` | 是 | `sNN.pMM`，来自 `sections.json` |
| `confidence` | 否 | `high` / `medium` / `low`，缺省按 `medium` 导出 |

## 2. nanopub.json（三段结构）

```json
{
 "assertion": {"assertions": [
   {"id": "a1", "uri": "urn:nanopub:37d03ece45c8c6fc", "text": "...",
    "subject": "...", "predicate": "has_property", "object": "...",
    "conditions": "", "confidence": "high"}
 ]},
 "provenance": [
   {"assertion_id": "a1", "source_id": "paper-...", "doi": "10.0000/...",
    "paragraph_id": "s02.p01", "quote": "...", "char_span": [120, 214]}
 ],
 "pubinfo": {"creator": "nanopub-assertion-builder", "created": "2026-01-15T00:00:00Z",
             "license": "CC-BY-4.0", "template": "nano-pub/1"}
}
```

- `provenance` 是**逐条**列表：每条断言一份来源记录，字段与题面一致
  （`source_id / doi / paragraph_id / quote / char_span`）。
- `char_span` 是 `[start, end)`，相对**全文原始字符串**的字符下标；当证据只能在整个文档
  而非指定段落中命中时，`char_span` 为 `null`（不伪造偏移）。
- `uri` = `urn:nanopub:` + `sha256(text + "|" + source_id)` 的前 16 位十六进制；
  同一断言在同一来源下重跑得到同一 URI，改一个字符就会变。

## 3. result.json

| 键 | 内容 |
|---|---|
| `skill` | `nanopub-assertion-builder` |
| `status` | `success` / `partial` / `failed` |
| `main_result.assertions` | 归一化后的断言列表 |
| `main_result.nanopub` | 上述三段结构 |
| `main_result.checks` | `errors` / `warnings` |
| `main_result.metrics` | `assertions`、`evidence_resolved`、`atomic`、`overbroad`、`duplicates`（均为计数） |
| `output_contract` | 按 `case.json.output_contract` 回填，不得为 `null` |
| `uncertainty` | `warnings`、`human_review`、`missing_fields`、`next_step` |

## 4. sections.json

与 Notes Skill 相同：`{"source", "n_sections", "sections":[{id,title,level,start,end,paragraphs:[{id,text,start,end}]}]}`。
`paragraph_id` 只认 `sNN.pMM`；`s2.p3` 会被归一为 `s02.p03`。

## 5. 状态判定

```
无可读材料            -> failed
无 draft              -> partial（候选断言，+ next_step）
有 draft 且 0 硬错误   -> success
有 draft 且有硬错误    -> partial
draft 断言为空         -> partial（no_assertions）
```
