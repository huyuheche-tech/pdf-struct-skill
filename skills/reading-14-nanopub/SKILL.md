---
name: nanopub-assertion-builder
description: 把论文结论拆成可发布、可追溯的 Nanopublication 断言：每条断言只含一个可判定主张，绑定原文短引与段号（sNN.pMM），保留 under/when/only if 等条件，校验三元组完整、谓语在受控词表内、证据可解析、无过宽表述与重复，并导出 assertion/provenance/pubinfo 三段结构与稳定 URI。当任务涉及"纳米出版/Nanopublication/断言抽取/RDF 三元组/结论溯源"时使用。
---

# Nanopublication 断言：拆得细 + 对得上 + 追得回

## 0. 运行契约（先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，输入是 `/input/case.json` + 材料，成品写到 `/app/output/`。

```bash
# 第 1 步：切章节、出段号 + 句级候选断言（未核验，status=partial）
python scripts/run_case.py --outline

# 第 2 步：把断言写进 /app/work/draft.json（格式见 §3），再校验并导出 nanopub.json
python scripts/run_case.py --draft /app/work/draft.json
```

`run_case.py` 会写：

| 文件 | 内容 |
|---|---|
| `sections.json` | 章节、段号 `sNN.pMM`、字符偏移 |
| `nanopub.json` | `assertion` / `provenance` / `pubinfo` 三段结构 |
| `assertions.md` | 表：id / 断言 / 证据 / 位置 / 置信度 + URI 表 |
| `checks.json` | `errors`（硬失败）、`warnings`（需人工确认） |
| `result.json` | `case_id` + `output_contract` 全部字段 + `status/evidence/uncertainty/sources` |

`main_result` 含 `assertions`、`nanopub`、`checks`、
`metrics{assertions, evidence_resolved, atomic, overbroad, duplicates}`。

**预算**：64 次模型请求 / 900 秒 / 单回复 16384 token。建议按段分批（每次 1 节、5–10 条断言），
每批都带上该节的原文与段号，不要把整篇与全部断言塞进一个请求。

**资源**：≤50 个 UTF-8 文本文件、单文件 ≤500KB、合计 ≤2MB、无符号链接。

## 1. 用途与适用条件

把论文里的一条条结论，拆成**单一、可判定、可溯源**的断言，并导出带 provenance 的
Nanopublication 结构。评分关注「拆得细 / 对得上 / 追得回 / 读得懂」。

适用：有文本层的 PDF / Markdown / TXT；英文或中文论文；需要把结论发布为可引用单元。
不适用：扫描件（先 OCR）；需要写综述式笔记（用「结构化笔记」Skill）；需要跨篇图谱
（用「文献知识图谱」Skill）。

## 2. 硬约束（评分点逐条对应）

| 约束 | 本 Skill 怎么保证 | 失败 code |
|---|---|---|
| **拆得细** | 一条断言一个主张；`;`、中文并列、`and` 双主谓都判不原子 | `not_atomic` |
| **对得上** | evidence 必须是所引段落的连续子串，≤400 字符；条件句必须保留 conditions | `evidence_unresolved`、`evidence_too_long`、`condition_dropped` |
| **追得回** | 每条断言有 `source_id` + `paragraph_id`；导出 `char_span` 与稳定 URI | `source_missing` |
| **读得懂** | 三元组齐、谓语受控、不过宽、不重复 | `triple_incomplete`、`predicate_invalid`、`overbroad`、`duplicate_assertion` |

**不得**为了让检查变绿而删断言、改证据原文、去掉条件、把 `always` 悄悄改成 `often`
却保留原证据（要改就改到与原文字面一致）。

## 3. 操作流程

### 3.1 读输入，确认边界

1. `case.json` 可能有 `case_id / title / material / doi / created / output_contract`；
   声明了 `material` 时优先使用它。
2. 跑 `--outline`，检查 `sections.json` 的段号；`notes.json` 式的候选断言只是线索，
   每项带 `candidate: true`，**不能直接发布**。
3. 材料缺失或 PDF 无文本层：`status=failed`/`partial`，写进 `uncertainty`，不要编造引文。

### 3.2 写断言（模型做的事）

一条断言 = 一个主语 + 一个受控谓语 + 一个宾语 + 一句原文证据 + 段号 + 条件（如有）。

1. **拆句**：遇到 `;`、`and` 连接两个主谓、`while/whereas`、中文「并且/同时/以及」就拆。
2. **选谓语**：只从 7 个词表里选（见 `references/controlled-vocab.md`）。
   `improves / reduces / causes` 不是合法谓语，用 `has_property` 把结果放进 object。
3. **留条件**：原文 `under / when / only if / in the setting of / 在…条件下 / 当…时`，
   必须在 `conditions` 里写具体范围。
4. **防过宽**：原文 `in most cases` 就不要写 `always`；原文没 `all` 就不要写 `all`。
5. **引文**：从该段复制**一句**原文，20–200 字符（上限 400）；不要用省略号拼接。
6. **来源**：`source_id` 全文一致；`paragraph_id` 用 `sNN.pMM`。

### 3.3 校验与返修

```bash
python scripts/run_case.py --draft /app/work/draft.json
```

- `status=success`：0 个 error；warning 按 §4 处理；
- `status=partial`：读 `checks.json.errors`，**只改断言，不改检查器**；
- `status=failed`：没有可读材料，不要伪造断言。

### 3.4 交付

`nanopub.json` 是机器可读成品，`assertions.md` 是给人看的对照表。
`result.json.main_result.nanopub` 放三段结构；`assertions` 放归一化断言；`checks` 放错误与警告。
`uri` 由 `sha256(text|source_id)[:16]` 生成，同一断言重跑稳定。

## 4. warning 处置

| warning | 含义 | 处置 |
|---|---|---|
| `candidate_assertions` | 没给 draft，候选是句级切分 | 补 draft 后重跑 |
| `draft_unreadable` | draft 不是合法 JSON 对象 | 修 JSON，不要改名绕过 |
| `evidence_elsewhere` | 段落号写错，但全文能找到证据 | 改 `paragraph_id`；`char_span` 会置空 |
| `no_assertions` | draft 的断言列表为空 | 补断言；空列表不算完成 |

## 5. 异常处理

| 情况 | 动作 |
|---|---|
| 没有可读材料 | `status=failed`，`uncertainty.warnings=[{code:no_material}]`，不写假断言 |
| PDF 无文本层 | `status=partial`，提示先 OCR；不要把空文本当原文 |
| 断言跨段 | 判 `evidence_unresolved`；缩短到本段一句，或拆成两条 |
| 中文论文 | 断言用中文，`predicate` 仍用英文受控词表 |
| 同一结论多处出现 | 只保留证据最强的一条；重复会被 `duplicate_assertion` 拦下 |
| 超出预算 | 先交已完成章节（`status=partial`），`next_step` 写明剩余章节 |

## 6. 自检清单（提交前逐条打勾）

- [ ] 每条断言只有一个主张，没有未拆的 `;` / `and` 双主谓；
- [ ] `predicate` 全部在 7 个受控词表内；
- [ ] 每条 evidence 能在对应 `sNN.pMM` 原文逐字找到，且 ≤400 字符；
- [ ] 原文有条件线索的断言都有 `conditions`，且写的是具体范围；
- [ ] 没有 `all/always/never/every` 超出证据支撑的表述；
- [ ] 每条都有 `source_id` + `paragraph_id`；
- [ ] `nanopub.json` 三段齐全，`char_span` 不为凭空编造；
- [ ] `checks.json.errors` 为空，或无法消除的都在 `uncertainty` 说明。

## 7. 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/run_case.py` | 运行入口（`--outline` / `--draft`） |
| `scripts/nanopub_builder.py` | 段落切分、断言校验、nanopub 导出 |
| `scripts/skillkit.py` | 公共库（读文件、PDF 文本、`check_quote`、契约回填） |
| `references/assertion-schema.md` | `draft.json` / `nanopub.json` / `result.json` 字段契约 |
| `references/controlled-vocab.md` | 7 个谓语、原子性、条件与证据规则 |
| `references/check-rules.md` | 每个 code 的触发条件、误报边界、返修 |
| `examples/` | 最小调用示例（输出标 EXAMPLE，非平台案例） |
| `tests/cases/` | 3 个本地自造案例 |

## 8. 边界与诚实声明

- 本 Skill **不判断断言在科学上是否成立**，只保证拆得原子、证据对得上、条件没丢、话没说满。
- 不联网核验 DOI 或来源真实性；`source_id`/`doi` 只做非空与透传。
- 跨段证据不支持；段落号错但全文能命中只给 warning，不伪造 `char_span`。
- `tests/` 的 3 个案例与 `examples/` 都是**本地自测，不是平台正式案例**，材料为自造，
  不能拿来冒充评测结果。
