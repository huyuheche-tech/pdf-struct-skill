---
name: bilingual-translation-guard
description: 把科研论文/摘要逐段译成中文并输出可核验的双语对照：锁定术语表、稳定段号、逐段校验数字/单位/引用/公式/否定与限定强度，译不准的地方显式标注。当任务涉及"翻译论文/摘要/方法段""中英对照""术语统一""译文核验"时使用。
---

# 文献翻译：术语锁定 + 段号对齐 + 逐段核验

## 0. 运行契约（先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，案例在 `/input/case.json` + `task.md`，成品写到 `/app/output/`。

```bash
# 第 1 步：出计划（段号、锁定的术语、每段必须保留的数字/引用/公式）
python scripts/run_case.py --plan-only

# 第 2 步：把译文写进 /app/work/draft.json（格式见下），再校验并出成品
python scripts/run_case.py --draft /app/work/draft.json
```

`run_case.py` 会写：

| 文件 | 内容 |
|---|---|
| `plan.json` | 每一段的 `id / zone / source / locked_terms / numbers / citations / formulas` |
| `translation.md` | 段号、位置、原文、译文、校验结果五列的双语对照表 |
| `checks.json` | `errors`（硬失败）、`warnings`（需人工确认）、逐段报告、术语一致性矩阵 |
| `result.json` | 平台契约：`case_id` + `output_contract` 全部字段 + `status/evidence/uncertainty/sources` |

**draft.json 格式（只接受这一种）**

```json
{"segments": [
  {"id": "p001", "target": "第一段译文"},
  {"id": "p002", "target": "第二段译文"}
],
 "back_translation": {"p001": "可选的回译文本"}}
```

规则：`id` 必须与 `plan.json` 一一对应，**不能合并、拆分、改号、漏段**；同一 `id` 只能出现一次。

**预算**：64 次模型请求 / 900 秒 / 单回复 16384 token。建议每 8–12 段发一次请求，每次请求都带上
`plan.json` 里该批段落的 `locked_terms`，不要一次塞整篇。

## 1. 用途与适用条件

把一篇论文（或摘要、方法段、图注）译成目标语言，产出**能逐段回查**的双语对照，而不是一段读起来通顺的译文。

适用：有文本层的 PDF / Markdown / TXT；中英互译；长文分段；有术语表或无术语表（自动抽候选）。
不适用：扫描件（先让「文献文档解析」Skill 走 OCR 分支拿到文本）；需要润色而非翻译的稿件（用「学术语言润色」Skill）。

## 2. 四个硬约束（评分点逐条对应）

| 约束 | 本 Skill 怎么保证 | 失败时 |
|---|---|---|
| **术语稳** | 术语表在 `plan.json` 里逐段下发；校验器要求每个锁定译名在该段译文中出现；`checks.json.glossary_matrix` 按 title/abstract/body/caption 分列 `命中/出现` | 记 `term_missing`，`status=partial`，不许改术语表绕过 |
| **段落全** | 段号由源文生成（`p001…`），draft 必须全覆盖；重复/未知/缺失都单独报错 | `missing_segment` / `duplicate_segment` / `unknown_segment` |
| **关系准** | 数字与单位多重集比对、引用标记逐字比对、公式/环境逐字比对、否定与限定词极性比对 | `number_missing` / `citation_missing` / `formula_changed` / `negation_lost`；`hedge_lost` 记 warning |
| **可核验** | 每段译文对应一个段号；`translation.md` 五行对照；`checks.json` 逐段列问题 | 人工可按段号回原文 |

**不得**为了让检查变绿而改数字、删引用、把否定句改成肯定句、把 `may` 译成「证明」。这些正是评委要看的失败模式。

## 2.9 题面四问对齐（评审核对用）

| 题面关注 | 本 Skill 的确定性保证 | 失败信号 | 不覆盖 |
|---|---|---|---|
| 术语稳 | 术语表逐段下发；锁定译名必须出现；按 title/abstract/body/caption 统计 | `term_missing` | 某刊官方译法 |
| 段落全 | `p001…` 全覆盖；缺/重/未知段号各自报错 | `missing_segment` / `duplicate_segment` / `unknown_segment` | 原文本身缺段 |
| 关系准 | 数字/单位、引用、公式逐字；否定与 hedge 极性 | `number_missing` / `citation_missing` / `formula_changed` / `negation_lost` | 指代、因果/让步的完整解析 |
| 可核验 | 每段五行对照 + `checks.json` 逐段问题 | — | 译文是否优美 |

### 2.10 交付自证字段（结果里直接读，不用自述）

`result.json` 顶层固定带三块**由实际运行算出来**的记录，供逐条复核：

| 字段 | 内容 | 对应题面要求 |
|---|---|---|
| `delivery_manifest` | `/app/output` 里真实写出的每个文件：文件名、字节数、sha256 前 16 位、是否可编辑 | 「结果可继续编辑」「可核验性」 |
| `change_record` | `modification_log`（本次改动台账及其来源字段）、`human_confirmation`、`material_gaps`、`anomalies` | 「版本与边界：修改差异、人工确认项、材料缺口和异常」 |
| `requirement_coverage` | 题面四个关注点逐条给 `satisfied`，命中的真实错误码放 `failed_checks`，只提示不判错的放 `advisory_checks`；`checks_watched` 列出每个码本次是 error / warning / 未触发 | 「完整性」「可核验性」 |

映射表在 `environment/requirements.json`（题面四问 → 引擎真实失败码），不是评委自评表。
例如漏译一段会把「段落全」标 false 并给出 `p0NN` 段号。

## 3. 操作流程

### 3.1 读输入，确认边界

1. `case.json` 里可能有 `source_language / target_language / glossary / domain / audience`；
   材料可能是 PDF、`material.md`、`source.txt`，也可能有 `glossary.csv`。**按实际文件读，不要按文件名猜内容。**
2. 运行 `--plan-only`，检查 `plan.json`：
   - `n_segments` 是否等于你看到的段落数；
   - `zones` 是否把标题/摘要/正文/图注分开了；
   - `glossary` 是否为空。为空时先做术语抽取（§3.2）。
3. 材料缺失、语言不明、术语表冲突：写进 `result.json.uncertainty`，不要猜。

### 3.2 术语表：先锁定，再翻译

- 有术语表：直接用。同一 source 出现两个 target 时，取**出现次数多**的；仍相同则标 `conflict` 并在
  `uncertainty.human_review` 里列出，不要自行合并。
- 无术语表：从 `plan.json` 的 `locked_terms` 为空这一事实出发，按下面顺序抽 10–30 条：
  1. 摘要与标题里的缩写（`LLM`、`MRI`、`F1`）；
  2. 反复出现的多词术语（`attention mechanism`、`residual connection`）；
  3. 方法名、数据集名、指标名（保持原文或按领域惯例，不要意译）。
- 把术语表写进输入目录的 `glossary.csv`（`source,target,note`）；引擎会自动读取该文件，也可以直接写进 `case.json.glossary`。
  再重跑 `--plan-only`。术语表一旦确定，**整篇不得换译名**。

### 3.3 分段翻译（模型做的事）

按 `plan.json` 的段号逐段翻译。每段遵守：

1. **数字、单位、百分比**原样保留（`18.4%`、`5 mg/day`、`p<0.001`）。
2. **引用标记**原样保留：`[12]`、`[3-5]`、`\cite{key}`；作者-年份可本地化为「Smith 等（2020）」，
   但年份和第一作者必须保留。
3. **公式**原样保留：`$...$`、`\(...\)`、`equation/align` 环境不翻译、不改写。
4. **否定与限定**：`not / no / fail to` 必须译出否定；`may / suggest / indicate / likely` 不得升级为
   「证明 / 表明事实」；`only / except / under the condition` 的限定范围不能扩大。
5. **指代**：`it / they / this method` 要译成明确名词，不写「它」了事。
6. 译不准的术语：写 `【待定：<原文>】`，不要编一个看起来专业的词。

### 3.4 校验与返修

```bash
python scripts/run_case.py --draft /app/work/draft.json
```

- `status=success`：0 个 error。仍有 warning 的段落按 §4 处理。
- `status=partial`：读 `checks.json.errors`，**只改译文，不改检查器**；改完重跑，直到 error 清零或
  确认无法消除（例如源文本身残缺），把无法消除的写进 `uncertainty`。
- 同一段重复翻译时，先与上一版对比：段号变了没有、数字少了没有、术语换了没有。

### 3.5 交付

`translation.md` 是给人看的成品；`result.json` 是给平台读的契约。两者都必须存在。
`result.json.main_result.translation` 里放 `translation.md` 全文，`segments` 里放逐段结构，
`glossary` 放术语矩阵，`checks` 放错误与警告。

## 4. warning 的处置（不是错误，但必须交代）

| warning | 含义 | 处置 |
|---|---|---|
| `hedge_lost` | 原文有「可能/提示」，译文读起来像确定结论 | 改译文，或在 `uncertainty.human_review` 标注 |
| `number_added` | 译文多出原文没有的数字 | 多半是「一/二」被写成阿拉伯数字，改成中文数词 |
| `citation_localised` | 作者-年份按中文惯例改写 | 可接受，保留第一作者与年份即可 |
| `length_outlier` | 译文字符数 < 源文 25% 或 > 300% | 检查是否漏译/扩写 |
| `back_translation_diverges` | 回译与原文相似度 < 0.45 | 检查漏译；不要用回译替代原文核对 |

## 5. 异常处理

| 情况 | 动作 |
|---|---|
| 没有可读材料 | `status=failed`，`uncertainty.warnings=[{code:no_material}]`，不写假译文 |
| PDF 无文本层 | `status=partial`，提示先走「文献文档解析」的 OCR 分支；不要把空文本当原文 |
| 语言混杂（中英日混排） | 逐段标注语言，只译目标语段；其余原样保留并记 warning |
| 术语表内部冲突 | 不自动合并；`conflict` + 人工确认清单 |
| 原文残缺/截断 | 该段 `target` 写 `【原文截断，未译】`，并在 `uncertainty` 写明缺在哪一段；不要补全 |
| 超出预算 | 先交已译段落（`status=partial`），`uncertainty.next_step` 写明剩余段号 |

## 6. 自检清单（提交前逐条打勾）

- [ ] `plan.json` 的段号与 `translation.md` 的行号一一对应；
- [ ] `checks.json.errors` 为空，或每条无法消除的 error 都在 `uncertainty` 里说明了原因；
- [ ] 术语矩阵里没有 `0/n` 的行（有就是整段没用锁定译名）；
- [ ] 抽查 3 段：数字、引用、公式与原文逐字一致；
- [ ] 抽查 1 段否定句、1 段限定句：语义强度没有被改写；
- [ ] `result.json` 的 `output_contract` 字段没有 `null`（除非契约本身要求可为空）。

## 7. 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/run_case.py` | 运行入口（两阶段） |
| `scripts/translate_guard.py` | 分段、术语、数字/引用/公式/否定校验 |
| `scripts/skillkit.py` | 公共库（读文件、PDF 文本、契约回填） |
| `references/glossary-policy.md` | 术语抽取与冲突处理规则 |
| `references/check-rules.md` | 每条检查的判据、误报边界、返修建议 |
| `references/segment-schema.md` | `plan.json` / `draft.json` / `result.json` 字段契约 |
| `examples/` | 最小调用示例（示例输出已标注 EXAMPLE） |
| `tests/cases/` | 3 个本地自测案例（非平台正式案例） |

## 8. 边界与诚实声明

- 本 Skill **不判断译文是否优美**，只保证「不丢段、不换术语、不改数字/引用/公式、不反否定」。
- 本地 `tests/` 里的 3 个案例是自造的管线测试，**不是**平台正式案例，也不能拿来冒充评测结果。
- 没有术语表时，`glossary` 只给候选，不假装是领域标准译名。
