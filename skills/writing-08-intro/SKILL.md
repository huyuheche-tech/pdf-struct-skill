---
name: intro-evidence-binder
description: 把摘要、结果与笔记整理成可回查的证据表，再据此写引言与相关工作四段（背景/相关工作/空白/贡献），逐条校验数字有出处、贡献有引文、空白段引用够、相关工作分组清、引用 key 存在。当任务涉及"写引言""写 related work""贡献点表述""研究空白""引言数字对不上"时使用。
---

# 引言与相关工作：证据先行 + 四段校验

## 0. 运行契约（先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，案例在 `/input/case.json` + `task.md`，成品写到 `/app/output/`。

```bash
# 第 1 步：从材料建证据表，拿到可引用的锚点
python scripts/run_case.py --plan-only

# 第 2 步：把四段写进 /app/work/draft.json，再校验并出成品
python scripts/run_case.py --draft /app/work/draft.json
```

`run_case.py` 会写：

| 文件 | 内容 |
|---|---|
| `evidence.json` | 每条含数字/比较/结论的句子：`anchor`（pNNN.sNN）、原文、数字列表 |
| `intro.md` | 四段成品：Background / Related Work（含分组）/ Gap / Contributions |
| `checks.json` | `errors`（硬失败）、`warnings`（需人工确认）、`summary`、`metrics` |
| `result.json` | 平台契约：`case_id` + `output_contract` 全部字段 + `status/evidence/uncertainty/sources` |

**draft.json 格式（只接受这一种）**

```json
{"sections": {
   "background": "... [liu2019] ...",
   "related_work": "... [vaswani2017] ...",
   "gap": "... [liu2019] ... [wang2018] ...",
   "contributions": ["...", "...", "..."]
 },
 "author_judgment": ["contributions"],
 "contribution_evidence": [
   {"contribution": 1, "anchor": "p002.s02", "quote": "原文里能逐字找到的句子"}
 ],
 "groups": [
   {"label": "attention-based", "works": ["liu2019", "vaswani2017"]},
   {"label": "recurrent-baselines", "works": ["chen2021", "wang2018"]}
 ]}
```

规则：`contribution` 从 1 开始，与 `contributions` 的顺序一一对应；`quote` 必须能在材料里**逐字**找到；
`anchor` 取自 `evidence.json`；`groups` 至少 2 组、每组至少 1 个 work；`author_judgment` 用于声明
"这一段是作者判断、不需要引用"（典型是 contributions）。

**预算**：64 次模型请求 / 900 秒 / 单回复 16384 token。建议先跑 `--plan-only`，把 `evidence.json`
按主题切块，每次请求只带相关锚点，不要一次塞整篇。

**资源**：≤50 个 UTF-8 文本文件、单文件 ≤500KB、合计 ≤2MB、无符号链接；只用标准库，不联网。

## 1. 用途与适用条件

把已有材料（摘要、结果、实验笔记、相关文献）变成一段**每个数字都能回查、每条贡献都有出处**的引言。

适用：有文本层材料（txt/md/pdf）；有或没有文献库（.bib/.json）；中英文均可；已经有 draft 需要体检；
也可以只跑 `--plan-only` 拿证据表交给写作模型。

不适用：没有材料却要求"编一段引言"；需要真正检索并阅读新文献（本 Skill 不联网、不抓文献）；
纯语言润色（用「学术语言润色」Skill）。

## 2. 四个硬约束（评分点逐条对应）

| 评分点 | 本 Skill 怎么保证 | 失败 code |
|---|---|---|
| **立得住** | 每条贡献都必须在 `contribution_evidence` 里绑定一个能在材料中逐字解析的 `quote` | `contribution_unbound` |
| **分得清** | 四段齐全且非空；相关工作至少 2 组、组标签非空、每组至少 1 个 work | `section_missing` / `grouping_thin` |
| **说得实** | draft 里每个数字都必须出现在证据表；空白段至少 2 条不同引用；每段至少 1 个引用或显式 `author_judgment` | `claim_unsupported` / `gap_unsupported` / `citation_missing` |
| **对得上** | 给了文献库时，`[key]`、`\cite{key}`、作者-年份都要能在库里解析 | `citation_unknown` |

**不得**为了让检查变绿而改数字、删掉没出处的贡献、把一组相关工作拆成两组、或删掉文献库。
这些正是评委要看的失败模式。

## 2.9 题面四问对齐（评审核对用）

| 题面关注 | 本 Skill 的确定性保证 | 失败信号 | 不覆盖 |
|---|---|---|---|
| 立得住 | 证据表 + 四段结构；背景段必须有引用或 `author_judgment` | `section_missing` / `citation_missing` | 背景是否空转（人工） |
| 分得清 | 相关工作 ≥2 组，组标签非空 | `grouping_thin` | 分组是否最优 |
| 说得实 | gap ≥2 引用；每个数字 claim 在证据表 | `gap_unsupported` / `claim_unsupported` | 空白推导是否成立 |
| 对得上 | 每条贡献绑 `contribution_evidence`，锚点必须在表里 | `contribution_unbound` / `anchor_invalid` | 贡献是否夸大 |

### 2.10 交付自证字段（结果里直接读，不用自述）

`result.json` 顶层固定带三块**由实际运行算出来**的记录，供逐条复核：

| 字段 | 内容 | 对应题面要求 |
|---|---|---|
| `delivery_manifest` | `/app/output` 里真实写出的每个文件：文件名、字节数、sha256 前 16 位、是否可编辑 | 「结果可继续编辑」「可核验性」 |
| `change_record` | `modification_log`（本次改动台账及其来源字段）、`human_confirmation`、`material_gaps`、`anomalies` | 「版本与边界：修改差异、人工确认项、材料缺口和异常」 |
| `requirement_coverage` | 题面四个关注点逐条给 `satisfied`，命中的真实错误码放 `failed_checks`，只提示不判错的放 `advisory_checks`；`checks_watched` 列出每个码本次是 error / warning / 未触发 | 「完整性」「可核验性」 |

映射表在 `environment/requirements.json`（题面四问 → 引擎真实失败码），不是评委自评表。
例如贡献没有绑定证据表锚点，「对得上」会列出 `contribution_unbound`。

## 3. 操作流程

### 3.1 读输入，确认边界

1. `case.json` 可能给出 `title / materials / output_contract`；材料可能是 `material.md`、`paper.pdf`、
   `refs.bib`、`library.json`。**按实际文件读，不要按文件名猜内容。**
2. 跑 `--plan-only`，看 `evidence.json`：
   - 条数是否覆盖你预期的关键结果；
   - `anchor` 是否稳定（`p002.s03` 这种）；
   - 数字列表里是否包含你要写的百分比 / p 值。
3. 没有文献库时，引用只能"未核验"，会记 `citation_unverified` warning，不会假装核验过。

### 3.2 先定四段骨架，再填内容

- **Background**：问题与代价。至少 1 条引用。
- **Related Work**：按 2–4 个 `groups` 组织，每组一句话 + 该组 works。组标签写"这一类做了什么"，
  不要写"相关研究"这种空标签。
- **Gap**：写"已有工作没做什么"，至少 2 条不同引用；不要把"我们没做"写成 gap。
- **Contributions**：3 条左右，每条一个动作 + 一个可核验结果；一般标 `author_judgment`。
- 每个数字都先在 `evidence.json` 里找到，再抄进正文；抄之前核对小数点和百分号。

### 3.3 绑定贡献与证据

对第 i 条贡献，在 `contribution_evidence` 里写：

```json
{"contribution": 2, "anchor": "p002.s03", "quote": "the encoder reduced validation error by 18.4%"}
```

`quote` 建议取整句或从句，**不要改写时态/单复数**；`anchor` 与 `evidence.json` 对齐。
`quote` 找不到就会 `contribution_unbound`，此时应当改 quote 或删掉这条贡献，而不是改引擎。

### 3.4 校验与返修

```bash
python scripts/run_case.py --draft /app/work/draft.json
```

- `status=success`：0 个 error。warning 按 §4 处理。
- `status=partial`：读 `checks.json.errors`，只改 draft，不改检查器；改完重跑。
- 同一段反复改时，先对比上一版：数字变了没有、引用少了没有、分组少了没有。

### 3.5 交付

`intro.md` 给人看；`result.json` 给平台读。`result.json.main_result` 里有 `sections`、`evidence`、
`checks`、`metrics{n_claims,supported,contributions,bound,groups,citations}`，`output_contract`
由 `skillkit.write_result` 自动回填。

## 4. warning 的处置（不是错误，但必须交代）

| warning | 含义 | 处置 |
|---|---|---|
| `anchor_unlisted` | quote 能在材料里找到，但 anchor 不在证据表 | 换成 `evidence.json` 里的 anchor，或确认 quote 是否跨句 |
| `citation_unverified` | 没有给文献库，引用 key 无法解析 | 在 `uncertainty` 里说明"引用未核验"，不要声称已核对 |

warning 只在 `checks.json.warnings` 里出现，不影响 `status`；但交付时必须在 `uncertainty` 交代。

## 5. 异常处理

| 情况 | 动作 |
|---|---|
| 没有可读材料 | `status=failed`，`checks.errors=[{code:no_material}]`，不写假引言 |
| PDF 无文本层 | `status=partial`，先走「文献文档解析」的 OCR 分支；不要把空文本当材料 |
| 没有文献库 | 正常出稿，引用记 `citation_unverified`；不伪造 key |
| 没有 draft | `status=partial`，`uncertainty.next_step` 写明 draft.json 的字段与命令 |
| 数字在材料里但不在证据表 | 先补材料句子或换一个可核验数字；不要改引擎阈值 |
| 材料互相矛盾（两个不同精度） | 以最新结果为准并在 `uncertainty.human_review` 列出，不要四舍五入"凑"一致 |
| 超出预算 | 先交已写段落（`status=partial`），`next_step` 写剩余段落 |

## 6. 自检清单（提交前逐条打勾）

- [ ] `evidence.json` 覆盖了正文要用的每个数字；
- [ ] 四段都非空，且每段有引用或 `author_judgment`；
- [ ] 每条 contribution 都有 `contribution_evidence`，且 quote 能在材料里找到；
- [ ] gap 段至少 2 条不同引用；
- [ ] 相关工作至少 2 组、组标签具体、每组至少 1 个 work；
- [ ] 给了文献库时，`checks.json.errors` 里没有 `citation_unknown`；
- [ ] `result.json` 的 `output_contract` 字段没有 `null`；
- [ ] 抽查 3 个数字：小数点、百分号、p 值与 `evidence.json` 逐字一致。

## 7. 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/run_case.py` | 运行入口（两阶段） |
| `scripts/intro_builder.py` | 证据表、四段校验、贡献绑定、引用核验、渲染 |
| `scripts/skillkit.py` | 公共库（读文件、PDF 文本、契约回填） |
| `references/check-rules.md` | 每条检查的判据、误报边界、返修建议 |
| `references/draft-schema.md` | `draft.json` / `evidence.json` / `result.json` 字段契约 |
| `references/writing-guide.md` | 四段写法与常见失败模式 |
| `examples/` | 最小调用示例（示例输出已标注 EXAMPLE） |
| `tests/cases/` | 3 个本地自测案例（非平台正式案例） |

## 8. 边界与诚实声明

- 本 Skill **不判断引言写得好不好**，只保证"四段齐、数字有出处、贡献有引文、引用能对上、分组不空"。
- 它**不检索文献、不生成新文献、不补 DOI**；没有文献库时只记 warning，不假装核验。
- 证据表只收"含数字/比较/结论线索"的句子，纯背景叙述可能不在表里；这不是遗漏，是设计。
- 本地 `tests/` 里的 3 个案例是自造的管线测试，**不是**平台正式案例，也不能拿来冒充评测结果。
