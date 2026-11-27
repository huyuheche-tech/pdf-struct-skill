---
name: structured-paper-notes
description: 把一篇论文读成可回查的结构化笔记：按章节切段并给每段稳定编号（sNN.pMM），把研究问题/数据/方法/发现/局限五字段、逐节摘要与知识点逐条锚定到原文引文，校验锚点可解析、字段齐全、发现与局限条数、知识点去重与章节覆盖。当任务涉及"论文总结/结构化笔记/文献卡片/精读/提炼要点"时使用。
---

# 文献总结与结构化笔记：章节切分 + 锚点回链

## 0. 运行契约（先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，输入是 `/input/case.json` + 材料（`material.md`/`.txt`/`.pdf`），
成品写到 `/app/output/`。

```bash
# 第 1 步：切章节、出段号索引 + 候选卡片（未核验，status=partial）
python scripts/run_case.py --outline

# 第 2 步：把笔记卡片写进 /app/work/draft.json（格式见 §3），再校验并出成品
python scripts/run_case.py --draft /app/work/draft.json
```

`run_case.py` 会写：

| 文件 | 内容 |
|---|---|
| `sections.json` | 章节标题、级别、字符偏移；每段 `sNN.pMM`、`text`、`start/end` |
| `notes.md` | 论文卡片表 + 逐节摘要表 + 知识点表 + 待修问题 |
| `notes.json` | `card` / `section_summaries` / `knowledge_points` / `candidate` |
| `checks.json` | `errors`（硬失败）、`warnings`（需人工确认）、`summary` |
| `result.json` | `case_id` + `output_contract` 全部字段 + `status/evidence/uncertainty/sources` |

`result.json.main_result` 含 `notes`、`sections`、`card`、`checks`、
`metrics{sections, covered, fields_complete, anchors_resolved, duplicates}`。

**预算**：64 次模型请求 / 900 秒 / 单回复 16384 token。建议先 `--outline` 拿到段号，再按章节分批
（每批 1–2 节）写卡片，不要把全文和全部笔记一次塞进一个请求。

**资源**：≤50 个 UTF-8 文本文件、单文件 ≤500KB、合计 ≤2MB、无符号链接。

## 1. 用途与适用条件

把论文变成**能逐条回原文**的笔记，而不是一段读起来顺的摘要。每条结论都带 `sNN.pMM` 段号与原文引文，
读者可以按段号跳回原文核对。

适用：有文本层的 PDF / Markdown / TXT；英文或中文论文；有标题层级（`#`、`1.`、`Abstract` 等）。
不适用：扫描件（先走「文献文档解析」的 OCR 分支）；需要逐段翻译（用「文献翻译」Skill）；
需要跨篇知识图谱（用「文献知识图谱」Skill）。

## 2. 硬约束（评分点逐条对应）

评分关注「对得上 / 留得住 / 找得回 / 用得上」。

| 约束 | 本 Skill 怎么保证 | 失败 code |
|---|---|---|
| **对得上** | 每个字段逐条锚定；`quote` 必须是该段连续子串（压缩空白后逐字比对） | `anchor_unresolved` |
| **留得住** | 段号由引擎生成，章节全覆盖；`findings` ≥2、`limitations` ≥1 | `section_uncovered`、`findings_thin`、`limitations_missing` |
| **找得回** | 每条摘要必须有锚点；`sections.json` 记录字符偏移 | `summary_unanchored` |
| **用得上** | 五字段齐全、知识点去重、逐节摘要 | `field_missing`、`duplicate_point` |

**不得**为了让检查变绿而删字段、删锚点、改写引文或把两条发现合成一条。

## 2.9 题面四问对齐（评审核对用）

| 题面关注 | 本 Skill 的确定性保证 | 失败信号 | 不覆盖 |
|---|---|---|---|
| 对得上 | 章节切分 + 逐节摘要覆盖所有一级章节 | `section_uncovered` | 论证顺序是否合理（人工） |
| 留得住 | 五字段齐全；findings≥2、limitations≥1 | `field_missing` / `findings_thin` / `limitations_missing` | 字段是否抓到重点 |
| 找得回 | 每字段 ≥1 锚点，quote 必须可解析 | `anchor_unresolved` | 跨段证据 |
| 用得上 | 知识点去重；`notes.json` 可检索 | `duplicate_point` | 笔记是否好用（人工） |

## 3. 操作流程

### 3.1 读输入，确认边界

1. `case.json` 可能有 `case_id / title / material / language / output_contract`。若声明了 `material`，
   引擎优先用它；否则取最长文本。
2. 先跑 `--outline`，检查 `sections.json`：
   - 章节数是否与论文一致；标题层级是否合理；
   - 段号是否覆盖了摘要、方法、结果、局限；
   - 候选卡片（`notes.json.card`，每项 `candidate: true`）只是线索，**不能直接当成品**。
3. 材料缺失、PDF 无文本层、章节切分明显错误：写进 `result.json.uncertainty`，不要猜。

### 3.2 写卡片（模型做的事）

按 `sections.json` 的段号写 `draft.json`：

- `research_question / data / method`：各一个对象，`text` 用中文概括，`anchor` 指向最直接的段；
- `findings`：≥2 条，每条一个独立发现（不同指标、不同条件、不同数据集都算独立）；
- `limitations`：≥1 条，优先用作者自己写的 limitation / future work；
- `section_summaries`：**每个一级章节一条**，摘要写"这一节起了什么作用"，不是复述标题；
- `knowledge_points`：3–8 条可复用的结论，避免同义重复。

引文规则：从该段原文**复制连续子串**，20–200 字符；跨段的句子要么截短，要么换段。

### 3.3 校验与返修

```bash
python scripts/run_case.py --draft /app/work/draft.json
```

- `status=success`：0 个 error，仍有 warning 的按 §4 处理；
- `status=partial`：读 `checks.json.errors`，**只改笔记，不改检查器**；改完重跑；
- `status=failed`：没有可读材料，不要伪造笔记。

常见修法见 `references/check-rules.md` 与 `references/anchor-rules.md`。

### 3.4 交付

`notes.md` 是给人读的成品，`result.json` 是平台契约，二者都必须存在。
`result.json.main_result.notes` 放 `notes.md` 全文；`card` 放结构化卡片；`checks` 放错误与警告。

## 4. warning 处置（不是错误，但必须交代）

| warning | 含义 | 处置 |
|---|---|---|
| `candidate_card` | 没给 draft，卡片是按线索词抽的候选 | 补 draft 后重跑；不要把候选当结论 |
| `draft_unreadable` | draft 不是合法 JSON 对象 | 修 JSON；不要重命名绕过 |
| `section_unknown` | `section_summaries.section_id` 对不上任何章节 | 改成 `sections.json` 里的真实 id |
| `number_mismatch`（人工） | 笔记数字与原文不一致 | 以原文为准改笔记 |

## 5. 异常处理

| 情况 | 动作 |
|---|---|
| 没有可读材料 | `status=failed`，`uncertainty.warnings=[{code:no_material}]`，不写假笔记 |
| PDF 无文本层 | `status=partial`，提示先走 OCR；不要把空文本当原文 |
| 标题层级混乱（全是一段） | 引擎退化为单章节 `Body`；在 `uncertainty` 说明，必要时人工指定章节 |
| 中英混排 | 按字面匹配，不做翻译对齐；quote 用原文语言 |
| 同一段支撑多个字段 | 允许；但每个字段仍要各自写 `anchor` + `quote` |
| 超出预算 | 先交已完成的章节（`status=partial`），`uncertainty.next_step` 写明剩余章节 |

## 6. 自检清单（提交前逐条打勾）

- [ ] `sections.json` 的章节数与论文一致，四个一级章节都有摘要；
- [ ] 每个字段、每条发现/局限、每条知识点都有 `anchor` + `quote`；
- [ ] 抽查 3 条 quote，能在对应 `sNN.pMM` 原文中逐字找到；
- [ ] `findings` ≥2 且彼此不是同一句话的改写；`limitations` ≥1；
- [ ] 知识点两两不重复（相似度 <0.90）；
- [ ] `checks.json.errors` 为空，或每条无法消除的 error 都在 `uncertainty` 说明原因；
- [ ] `result.json.output_contract` 没有 `null`。

## 7. 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/run_case.py` | 运行入口（`--outline` / `--draft`） |
| `scripts/notes_builder.py` | 章节切分、锚点解析、字段与去重校验、渲染 |
| `scripts/skillkit.py` | 公共库（读文件、PDF 文本、`check_quote`、契约回填） |
| `references/anchor-rules.md` | 章节/段号/引文判定规则与误报边界 |
| `references/notes-schema.md` | `draft.json` / `notes.json` / `result.json` 字段契约 |
| `references/check-rules.md` | 每个 code 的触发条件、误报边界、返修 |
| `examples/` | 最小调用示例（输出标 EXAMPLE，非平台案例） |
| `tests/cases/` | 3 个本地自造案例 |

## 8. 边界与诚实声明

- 本 Skill **不判断笔记写得好不好**：它只保证字段齐、锚点对、条数够、不重复。
- 引擎不验证「实验是否支持该结论」，只验证「原文确实这么写了」。
- 局限至少一条，**不保证**覆盖论文全部局限；跨语言不做翻译对齐。
- `tests/` 里的 3 个案例与 `examples/` 都是**本地自测，不是平台正式案例**，
  不能拿来冒充评测结果；案例材料为自造。
