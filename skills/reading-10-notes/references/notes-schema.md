# 数据契约：draft.json / notes.json / result.json

## 1. draft.json（模型写，唯一入口）

```json
{
  "card": {
    "research_question": {"text": "…", "anchor": "s01.p01", "quote": "…"},
    "data":              {"text": "…", "anchor": "s03.p01", "quote": "…"},
    "method":            {"text": "…", "anchor": "s03.p01", "quote": "…"},
    "findings": [
      {"text": "…", "anchor": "s04.p01", "quote": "…"},
      {"text": "…", "anchor": "s04.p01", "quote": "…"}
    ],
    "limitations": [
      {"text": "…", "anchor": "s04.p01", "quote": "…"}
    ]
  },
  "section_summaries": [
    {"section_id": "s01", "text": "…", "anchor": "s01.p01", "quote": "…"}
  ],
  "knowledge_points": [
    {"text": "…", "anchor": "s02.p01", "quote": "…"}
  ]
}
```

- `research_question` / `data` / `method` 必须是对象且 `text` 非空；
- `findings` ≥ 2 条、`limitations` ≥ 1 条；
- 每个条目至少一个锚点（`anchor` + `quote`）；
- 一个条目也可写成 `"anchors": [{"anchor": "...", "quote": "..."}, ...]`，引擎会逐个校验；
- `section_summaries` 必须覆盖全部一级章节，且每条都要有锚点；
- `knowledge_points` 用归一化文本比较，相似度 > 0.90 记重复。

## 2. notes.json（给人复查的中间件）

```json
{"title": "...", "candidate": false, "card": {...},
 "section_summaries": [...], "knowledge_points": [...],
 "fields_complete": ["research_question", "data", "method", "findings", "limitations"]}
```

无 draft 时 `candidate=true`，卡片每项都带 `candidate: true`，表示**未核验的候选**。

## 3. sections.json

```json
{"source": "material.md", "n_sections": 4,
 "sections": [{"id": "s01", "title": "Abstract", "level": 2,
               "start": 0, "end": 420, "n_paragraphs": 1,
               "paragraphs": [{"id": "s01.p01", "text": "...",
                               "start": 12, "end": 408}]}]}
```

`start/end` 是全文绝对字符偏移（Python 字符串下标，按 Unicode 码点计）。

## 4. result.json（平台契约）

| 键 | 内容 |
|---|---|
| `skill` | `structured-paper-notes` |
| `case_id` | 来自 case.json，回退到材料文件名 |
| `status` | `success` / `partial` / `failed` |
| `main_result.notes` | `notes.md` 全文 |
| `main_result.sections` | 章节 + 段落偏移摘要 |
| `main_result.card` | 论文卡片（draft 或候选） |
| `main_result.checks` | `errors` / `warnings` / `summary` |
| `main_result.metrics` | `sections`、`covered`、`fields_complete`、`anchors_resolved`、`duplicates` |
| `output_contract` | 按 `case.json.output_contract` 回填，不得为 `null` |
| `uncertainty` | `warnings`、`human_review`、`missing_fields`、`next_step` |

## 5. 状态判定

```
无可读材料            -> failed
无 draft              -> partial（+ next_step）
有 draft 且 0 硬错误   -> success
有 draft 且有硬错误    -> partial
```

`checks.json` 只放 `errors`（硬失败）与 `warnings`（需人工确认），不把 warning 混进 error。
