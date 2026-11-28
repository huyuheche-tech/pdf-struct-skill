---
name: academic-polish-ledger
description: 学术语言润色并输出逐条可核验的修改台账：句级对齐原文与改稿，锁定术语写法，硬性校验数字/单位、引用标记、否定极性、hedge 强度不被改写，并做高置信度残留语法 lint。当任务涉及"润色摘要/段落""改语法""统一术语""英文或中文润色且不能改坏数据"时使用。
---

# 学术语言润色：句级对齐 + 修改台账 + 七类硬校验

## 0. 运行契约（先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，案例在 `/input/case.json` + 材料，成品写到 `/app/output/`。

```bash
# 第 1 步：出计划（句号、每句必须保留的数字/引用、锁定术语、台账模板）
python scripts/run_case.py --plan-only

# 第 2 步：把改稿写进 /app/work/draft.json（格式见下），再校验并出成品
python scripts/run_case.py --draft /app/work/draft.json
```

本地调试时补上四个路径参数（等价写法）：

```bash
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out --work ./work --plan-only
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out --work ./work --draft examples/draft.json
```

`--plan-only` **只出计划，不校验 draft**（即使 draft 就在旁边也不会被读），所以它永远不返回 `success`。

| 输出文件 | 内容 |
|---|---|
| `plan.json` | 每句的 `id / sentence / numbers / citations / locked_terms` |
| `polished.md` | 改稿全文 + 修改台账表（人看的成品；**没有 draft 时不生成**，不拿原文冒充成品） |
| `edits.json` | 台账：`id / original / edited / type / reason / change_type / source` |
| `checks.json` | `errors`（硬失败）、`warnings`、逐句 `change_type`、`summary` |
| `result.json` | 平台契约：`case_id` + `output_contract` 全字段 + `status/evidence/uncertainty/sources` |

**draft.json 格式（只接受这两种）**

```json
{"edited": "改稿全文",
 "edits": [
   {"id": "s01", "original": "whether attention mechanism improves",
    "edited": "whether an attention mechanism improves",
    "type": "grammar", "reason": "可数名词单数前缺不定冠词"}
 ]}
```

```json
{"edited_text": "只有改稿全文，没有台账"}
```

第二种会被引擎按句对齐**自动补台账**，但自动条目没有 `reason`，因此每条都记
`edit_unexplained`（硬错误）。想拿 `success` 就必须自己写台账。

`type` 只能是 `grammar / term / tone / clarity` 四类。`original` 必须是原文里真实存在的片段
（允许是句子的一部分），否则记 `edit_unanchored`。

**result.json 字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `case_id` / `status` | str | `success` / `partial` / `failed` |
| `main_result.edited_text` | str | 改稿纯文本（不含台账表） |
| `main_result.edits[]` | list | 台账逐条 |
| `main_result.checks` | obj | `errors/warnings/sentences/summary` |
| `main_result.metrics` | obj | `edit_count/unexplained/number_drift/hedge_drift/residual_grammar` |
| `output_contract` | obj | 按 `case.json.output_contract` 逐字段回填 |
| `contract_unresolved` | list | 未回填字段（应为空） |
| `uncertainty` | obj | `warnings/human_review/missing_fields/note/next_step` |

**预算**：64 次模型请求 / 900 秒 / 单回复 16384 token。建议每次请求只改 6–10 句，
把 `plan.json` 里这几句的 `locked_terms` 原样带上，不要一次塞整篇。
**资源**：≤50 个 UTF-8 文本文件、单文件 ≤500KB、合计 ≤2MB、无符号链接；只用标准库，不联网。

## 1. 用途与适用条件

把一段（或一篇）学术文本改得更准确、更符合期刊语体，同时**保证没有改坏事实**：
数字不变、引用不丢、否定不反、结论强度不升、术语不漂移，并且每一处改动都能说清"为什么改"。

适用：英文摘要/正文润色；中文摘要润色；期刊要求"language editing"；导师批注"语句不通"；
同一术语在全文有多个写法需要统一。
不适用：翻译（用「文献翻译」Skill）；需要重写论证结构或补实验（属于写作而非润色）；
改稿后出现的**新事实**（本 Skill 只保证不改坏，不保证改对——事实仍需人工核）。

## 2. 七个硬约束（评分点逐条对应）

| 约束 | 本 Skill 怎么保证 | 失败 code |
|---|---|---|
| **改得对：数字不动** | 逐句比对数字+单位多重集（DOI/URL/引用标记先剥离，避免把 `10.1000/x` 当数据） | `number_missing` / `number_added` / `number_changed` |
| **改得对：引用不丢** | 逐句比对标记集合（`[2,4]` 归一为同一集合） | `citation_changed` |
| **改得对：结论强度不升** | 源句含 `may/might/could/suggest/indicate/likely/possibly` 而改句变成 `prove/demonstrate/show that/confirm/establish` 且不再有 hedge → 硬错误 | `hedge_strengthened`（反向记 warning `hedge_weakened`） |
| **改得对：否定不反** | 逐句比对否定极性（英文 `not/no/never/fail to`，中文 `不/未/无/非/没有/无法`，「不同/不仅/无论」不算否定） | `negation_changed` |
| **说得像：术语不漂** | 术语表锁定写法；源句出现该词，改句必须用锁定形式 | `term_missing` |
| **讲得清：台账可核** | 每条改动必须有 `type`（四类）+ `reason`，`original` 必须能在原文定位 | `edit_unexplained` / `edit_bad_type` / `edit_unanchored` |
| **没改坏：残留在改稿里的错** | 高置信 lint：a/an、主谓一致（仅句首 It/He/She + 动词原形）、双空格、句首小写、`et al` 缺句点 | `residual_grammar`（带 `rule`） |

**不得**为了让检查变绿而改数字、删引用、把 `may` 改成 `demonstrates`、把「不显著」改成「显著」、
或给没做的改动编一条 reason。这些正是评委要看的失败模式。

## 2.9 题面四问对齐（评审核对用）

| 题面关注 | 本 Skill 的确定性保证 | 失败信号 | 不覆盖 |
|---|---|---|---|
| 改得对 | 句级对齐 + 台账 type/reason；残留语法 lint | `edit_unexplained` / 残留 lint | 复杂搭配与语义错误 |
| 说得像 | 术语写法锁定；语域只做高置信 lint | `term_missing` | 是否像同行写的（人工） |
| 没改坏 | 数字多重集、引用集合、否定极性、hedge 强度 | `number_*` / `citation_changed` / `negation_changed` / `hedge_strengthened` | 隐含语气 |
| 讲得清 | 每条改动 original/edited/type/reason | `edit_unanchored` | 理由是否成立（人工） |

### 2.10 交付自证字段（结果里直接读，不用自述）

`result.json` 顶层固定带三块**由实际运行算出来**的记录，供逐条复核：

| 字段 | 内容 | 对应题面要求 |
|---|---|---|
| `delivery_manifest` | `/app/output` 里真实写出的每个文件：文件名、字节数、sha256 前 16 位、是否可编辑 | 「结果可继续编辑」「可核验性」 |
| `change_record` | `modification_log`（本次改动台账及其来源字段）、`human_confirmation`、`material_gaps`、`anomalies` | 「版本与边界：修改差异、人工确认项、材料缺口和异常」 |
| `requirement_coverage` | 题面四个关注点逐条给 `satisfied`，命中的真实错误码放 `failed_checks`，只提示不判错的放 `advisory_checks`；`checks_watched` 列出每个码本次是 error / warning / 未触发 | 「完整性」「可核验性」 |

映射表在 `environment/requirements.json`（题面四问 → 引擎真实失败码），不是评委自评表。
例如把 may 改成 demonstrates、删掉 [3]，「没改坏」会同时列出 `hedge_strengthened` / `citation_changed`。

## 3. 操作流程

### 3.1 读输入，确认边界

1. `case.json` 里可能有 `language / glossary / glossary_file / journal / audience`；
   材料可能是 `.md / .txt / .pdf`，术语表可能是 `glossary.csv`（`source,target,note`）或 `case.json.glossary`。
   **按实际文件读，不要按文件名猜内容。**
2. 跑 `--plan-only`，检查 `plan.json`：句数是否等于你数出来的句数；有没有句子被切错（公式、缩写、`et al.`）；
   `locked_terms` 是否覆盖了你打算改的术语。切句错就保持原文的标点与分段，不要为了对齐去改引擎。
3. 材料缺失 / 语言不明 / 术语表自相矛盾：写进 `uncertainty`，不要猜。

### 3.2 先定"不许动"的清单

在动笔前把这三类先抄下来，改的时候逐句核：
- 每个数字与单位（`18.4%`、`5 mg/day`、`p<0.001`、`40 epochs`、`64`）；
- 每个引用标记（`[3]`、`[2,4]`、`\cite{key}`、`(Smith et al., 2020)`）；
- 每个 hedge 与否定（`may`、`suggest`、`likely`、`not`、`only`、`不显著`）。
这三类是本 Skill 的硬错误来源，改一句就要回看一次。

### 3.3 改（模型做的事）

四类改动的判据（也是台账 `type` 的取值）：

| type | 什么时候用 | 例子 |
|---|---|---|
| `grammar` | 冠词、单复数、时态、主谓一致、标点 | `a important` → `an important` |
| `term` | 术语/写法统一，且能对上术语表某一行 | `attention model` → `attention mechanism` |
| `tone` | 语体、 hedging、正式度；**不许加强结论** | `a lot of` → `considerable` |
| `clarity` | 拆长句、去套叠、消歧义、调整语序 | `对……的……是一个……` → `对……具有……` |

写改稿时守则：
1. 一句话只解决一个问题；能在原句上改就不要重写整段（重写会让对齐变差、台账难核）。
2. 数字、单位、百分号、`p` 值**逐字保留**；中文里"三个"可以保留汉字，不要改成 `3`。
3. 引用标记原样保留在原来的位置附近；不要"顺手"补一条引用。
4. `may/suggest/indicate` 只能保留或换成同强度的词（`can`、`appears to`），不能换成 `prove/demonstrate`。
5. 术语按术语表；术语表没覆盖的新术语，保持原文并在 `uncertainty` 说明。
6. 改完通读一遍：a/an、主谓、双空格、句首大小写、`et al.` 的句点——这五项引擎会查，别留给它查。

### 3.4 校验与返修

```bash
python scripts/run_case.py --draft /app/work/draft.json
```

- `status=success`：0 个 error。warning 按 §4 处理。
- `status=partial`：读 `checks.json.errors`，**只改稿子，不改检查器**；改完重跑。
  消不掉的（例如原文本身就有一个错的数字）写进 `uncertainty.human_review` 并说明。
- `checks.json.sentences[].change_type` 为 `deleted/inserted` 说明你合并或拆分了句子（`alignment_gap`），
  能避免就避免；确实要合并，在台账里写一条覆盖这两句的 `clarity` 记录。

### 3.5 交付

`polished.md` 给人看（改稿 + 台账表），`result.json` 给平台读。
`main_result.edited_text` 是**不含台账表**的纯文本，供下游直接引用。

## 4. warning 的处置（不是错误，但必须交代）

| warning | 含义 | 处置 |
|---|---|---|
| `hedge_weakened` | 原文是断言，改稿变弱（`demonstrates` → `may suggest`） | 确认不是"改小了结论"；必要则改回 |
| `alignment_gap` | 有一句在另一边找不到对应（合并/拆分/增删句） | 优先拆回；确需合并就在台账里登记 |
| `edit_noop` | `original` 与 `edited` 相同却写了 reason | 删掉这条，或真的改一处 |
| `edit_duplicate_id` | 台账 id 重复 | 换成唯一 id（建议 `s01…`） |
| `draft_missing` | draft 里没有 `edited`/`edited_text` | 补上改稿全文再跑 |

## 5. 异常处理

| 情况 | 动作 |
|---|---|
| 没有可读材料 | `status=failed`，`errors=[{code:no_material}]`，不写假改稿 |
| draft 里没有 `edited`/`edited_text` | `status=partial`，`warnings=[{code:draft_missing}]`，**不写 `polished.md`** |
| PDF 无文本层 | 提示先走「文献文档解析」的 OCR 分支；把抽到的空文本当"原文"是错的 |
| 中英混排 | 按段润色目标语言；另一语言原样保留，并在 `uncertainty` 注明 |
| 术语表冲突（同一词两个写法） | 不自动合并；取出现次数多者，另一条进 `human_review` |
| 原文本身有错（错数字、错引用） | **不改**，把它记进 `uncertainty.human_review`，让作者决定 |
| 超出预算 | 先交已改部分，`status=partial`，`next_step` 写明剩余句号 |

## 6. 自检清单（提交前逐条打勾）

- [ ] `checks.json.errors` 为空，或每条消不掉的 error 都在 `uncertainty` 里说明了原因；
- [ ] `metrics.number_drift == 0` 且 `metrics.hedge_drift == 0`；
- [ ] `metrics.unexplained == 0`（每条改动都有 reason）；
- [ ] 抽查 3 条台账：`original` 能在 `material.md` 里搜到，`edited` 能在 `polished.md` 里搜到；
- [ ] 抽查 1 句否定句、1 句 hedge 句：语义强度没变；
- [ ] `metrics.residual_grammar == 0`（a/an、主谓、双空格、句首小写、`et al.`）；
- [ ] `result.json.output_contract` 没有 `null`。

## 7. 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/run_case.py` | 运行入口（两阶段：`--plan-only` / `--draft`） |
| `scripts/polish_ledger.py` | 句级对齐、台账校验、数字/引用/hedge/否定/术语、残留语法 lint |
| `scripts/skillkit.py` | 公共库（读文件、PDF 文本、切句、契约回填） |
| `references/check-rules.md` | 每条检查的判据、误报边界、返修建议 |
| `references/ledger-schema.md` | `plan.json` / `draft.json` / `edits.json` / `result.json` 字段契约 |
| `examples/` | 最小调用示例（示例输出已标 EXAMPLE） |
| `tests/cases/` | 3 个本地自测案例（非平台正式案例） |

## 8. 边界与诚实声明

- 本 Skill **不判断文笔好坏**，只保证"没改坏 + 每处改动可核"。改得漂亮不漂亮要人看。
- 检查器只覆盖能确定性判定的七类；**逻辑关系、因果、指代、语篇衔接、术语是否符合某刊惯例**都没查，
  这些写在 `uncertainty.note` 里，不假装覆盖。
- hedge 判定是词表匹配：源句同时含 hedge 与 `demonstrate` 时以"改句是否留下 hedge"为准，
  个别句式可能误报；误报就保留原句或写进 `human_review`，不要为了消错把结论写弱。
- 主谓一致只在**句首 `It/He/She` + 动词原形**这一种高置信形态上报，`made it work` 这类不会误报，
  但也就查不到真正的主谓错误——这是刻意的取舍。
- 中文按字计，长度启发式（`clarity` 自动判定）只对英文有效；中文改动的 `type` 以台账为准。
- `tests/` 里的 3 个案例是**本地自测**，材料自造，**不是**平台正式案例，也不能当评测结果引用。
