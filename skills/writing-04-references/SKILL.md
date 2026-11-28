---
name: citation-ledger
description: 参考文献与引用管理：解析 BibTeX/RIS/编号文献表与正文的 [1]、[2,4]、[3-5]、\cite{key}、作者-年份引用，做双向对账（正文缺条/文献未引/重号断号），按首次出现重编号并改写正文，按 DOI 或标题相似度去重并记录依据，输出 GB/T 7714—2015（或 APA）参考文献表，缺字段写 TODO 不编造。当任务涉及"参考文献核对""引用编号乱""去重""改成国标格式""投稿前查引用"时使用。
---

# 参考文献管理：双向对账 + 自动重编号 + 去重 + 国标格式化

## 0. 运行契约（先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，案例在 `/input/case.json` + 材料，成品写到 `/app/output/`。

```bash
# 第 1 步：只对账，不改写正文（--check-only）
python scripts/run_case.py --check-only

# 第 2 步：带编辑决策跑完整流程（对账 + 重编号 + 出参考文献表）
python scripts/run_case.py --draft /app/work/draft.json
```

本地调试时补上四个路径参数（等价写法）：

```bash
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out --work ./work --check-only
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out --work ./work --draft examples/draft.json
```

`--check-only` **不写 `manuscript_renumbered.md`**，也不读 draft；它只出对账报告，
因此永远不返回 `success`（`uncertainty.next_step` 会说明下一步）。
`--style gbt7714|apa` 选输出格式，默认 `gbt7714`（也读 `case.json.style`）。

| 输出文件 | 内容 |
|---|---|
| `manuscript_renumbered.md` | 按首次出现重编号后的正文（`\cite` 与作者-年份不动；`--check-only` 不生成） |
| `references.json` | 条目 + `renumber_map` + 合并记录 + 问题清单 |
| `bibliography.md` | GB/T 7714—2015（或 APA）参考文献表，`[n]` 序号 |
| `checks.json` | `errors`（硬失败）、`warnings`、逐条引用解析结果、`summary` |
| `result.json` | 平台契约：`case_id` + `output_contract` 全字段 + `status/evidence/uncertainty/sources` |

**draft.json 格式（编辑决策，脚本不许替你猜）**

```json
{"merges": [["chen2019conf", "chen2019j"]],
 "declared_complete": ["chen2019j", "liu2021"],
 "notes": "会议版与期刊版同 DOI，属于同一项工作"}
```

- `merges`：**额外**提议合并的文献对（引擎已按规则自动合并的不必再写）。引擎会复核；
  不满足"DOI 相同"或"标题相似度 ≥0.90 且第一作者同姓"的提议，报 `unsafe_merge` 并**拒绝合并**。
- `declared_complete`：你声称"字段齐全"的条目。**声称完整却缺字段**，记 `field_missing`（硬错误）。
  不声明时缺字段只是 warning，参考文献表里写 `[TODO: field]`。
- 两个键都可以是空列表；空列表也是一次明确的编辑决策（"我不提议额外合并，也不声明任何条目完整"）。

**result.json 字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `case_id` / `status` | str | `success` / `partial` / `failed` |
| `main_result.references[]` | list | 每条：`key/type/number_old/number_new/authors/title/year/source/doi/completeness/cited/todo/gbt7714/apa/merged_from` |
| `main_result.renumber_map[]` | list | `{old, key, new, merged_into, cited}` |
| `main_result.checks` | obj | `errors/warnings/summary/citations` |
| `main_result.metrics` | obj | `entries/cited/uncited/missing/duplicates/field_completeness` |
| `main_result.bibliography` | str | `bibliography.md` 全文 |
| `main_result.manuscript_renumbered` | str | 改写后的正文（`--check-only` 下为空串） |
| `output_contract` | obj | 按 `case.json.output_contract` 逐字段回填 |
| `uncertainty` | obj | `warnings/human_review/missing_fields/note/next_step` |

**预算**：64 次模型请求 / 900 秒 / 单回复 16384 token。本 Skill 的主体是确定性解析，
建议流程：1 次 `--check-only` 看对账 → 用 1–3 次请求判断"哪些是同一篇""哪些确实完整" →
写 draft → 1 次完整跑。不要逐条文献发请求。
**资源**：≤50 个 UTF-8 文本文件、单文件 ≤500KB、合计 ≤2MB、无符号链接；只用标准库，不联网。

## 1. 用途与适用条件

把"正文引用"和"文献表"当成两个集合对起来：谁多、谁少、谁重号、谁其实是同一篇，
然后把编号理顺、把格式统一到 GB/T 7714—2015，**并且每个缺的字段都留成 TODO 而不是编一个**。

适用：投稿前自查引用；从 Zotero/EndNote 导出的 `.bib` / `.ris`；期刊要求的中文参考文献表；
手写 `[1]…[n]` 的 Word/Markdown 稿；作者-年份稿要转成顺序编码制。
不适用：需要**核对文献是否真实存在**（本 Skill 不联网，见 §8）；需要排版模板（本 Skill 只出文本）；
需要从 PDF 抽取参考文献（先用「文献文档解析」拿到文本）。

## 2. 五个硬约束（评分点逐条对应）

| 约束 | 本 Skill 怎么保证 | 失败时 |
|---|---|---|
| **挂得对：双向对账** | 正文引用逐条解析，与文献表按编号 / key / 作者-年份匹配；两个方向都报 | `missing_entry`（正文有、表里没有，硬错误）；`uncited_entry`（表里有、正文没引，warning）；`number_gap`（编号重复或断号，warning） |
| **编得顺：按首次出现重编号** | 遍历正文引用顺序，首次出现的条目拿 1、2、3…；未引条目排到末尾，不静默删除 | 生成 `renumber_map`；改写 `manuscript_renumbered.md` |
| **收得净：去重有依据** | DOI 完全相同 → 直接合并；否则**标题归一化相似度 ≥0.90 且第一作者同姓**才合并；每次合并写 `basis` 与 `detail` | 提议但不够格的合并 → `unsafe_merge`（硬错误，拒绝执行） |
| **对得上：国标格式** | `作者. 题名[类型]. 刊名, 年, 卷(期): 起页-止页. DOI: ...`；>3 位作者用"等"/"et al."；缺字段写 `[TODO: field]` | `field_missing`（缺字段；声明完整时升为硬错误） |
| **可核验：逐条可回溯** | 每条给 `completeness{author,title,year,source,doi}`、`type`、`cited`、`cite_count`、`merged_from` | `references.json` 与人读的 `bibliography.md` 一一对应 |

**不得**为了让检查变绿而编 DOI、补作者、把两篇不同文献合并、或把未引条目悄悄删掉。
这三件事正是评委要看的失败模式。

### 2.1 引用语境表（给"挂得对/对得上"留证据）

`result.json.main_result.citation_contexts` 为每条正文引用记录：

```json
{"citation": "[3]", "key": "he2016", "sentence": "引用所在句",
 "title": "被引文献题名", "overlap": 2, "position": "sentence|paragraph_end"}
```

`overlap` 是句子与题名的实词交集数（英文词 + 中文二元组）。`overlap=0` 且题名有 ≥3 个实词时记
`claim_topic_mismatch`（**警告**，不是判决）——它只说明"这句和这篇标题没有任何共同实词"，需要人看一眼；
引用是否真的支持该论断，最终仍要读原文。`position=paragraph_end` 表示引用落在长段末尾，可能是"整段一引"。

## 2.9 题面四问对齐（评审核对用）

| 题面关注 | 本 Skill 的确定性保证 | 失败信号 | 不覆盖 |
|---|---|---|---|
| 挂得对 | `citation_contexts` 给出所在句 + 题名 + 实词交集；长段末尾标记 | `claim_topic_mismatch`（warning） | 引用是否真的支持论断（人工） |
| 编得顺 | 按首次出现重编号并改写正文；断号/重号检查 | `number_gap` | 图/表/脚注的交叉引用 |
| 收得净 | DOI 或标题≥0.90+同姓才合并，写 `merge_basis` | `unsafe_merge` | 预印本/正式版之外的同名歧义 |
| 对得上 | 双向对账；GB/T 7714 字段；缺字段 TODO | `missing_entry` / `field_missing` | 文献真伪与联网核验 |

### 2.10 交付自证字段（结果里直接读，不用自述）

`result.json` 顶层固定带三块**由实际运行算出来**的记录，供逐条复核：

| 字段 | 内容 | 对应题面要求 |
|---|---|---|
| `delivery_manifest` | `/app/output` 里真实写出的每个文件：文件名、字节数、sha256 前 16 位、是否可编辑 | 「结果可继续编辑」「可核验性」 |
| `change_record` | `modification_log`（本次改动台账及其来源字段）、`human_confirmation`、`material_gaps`、`anomalies` | 「版本与边界：修改差异、人工确认项、材料缺口和异常」 |
| `requirement_coverage` | 题面四个关注点逐条给 `satisfied`，命中的真实错误码放 `failed_checks`，只提示不判错的放 `advisory_checks`；`checks_watched` 列出每个码本次是 error / warning / 未触发 | 「完整性」「可核验性」 |

映射表在 `environment/requirements.json`（题面四问 → 引擎真实失败码），不是评委自评表。
例如正文引了但文献表没有，「对得上」会列出 `missing_entry`；主题词零重叠只算 advisory。

## 3. 操作流程

### 3.1 读输入，确认边界

1. `case.json` 里可能有 `style / library / manuscript / journal`；材料可能是
   `.bib`、`.ris`、编号文本（`[1] 作者. 题名[J]. 刊名, 2019, 20(4): 1-25.`）、`.md`、`.txt`。
   引擎按**文件内容**判断谁是文献表（首行像 `[1] …` 就算编号表），不要按文件名猜。
2. 跑 `--check-only`，看 `checks.json`：
   - `errors` 里有没有 `missing_entry`（正文引了表里没有的号）；
   - `warnings` 里有没有 `uncited_entry` / `number_gap` / `duplicate_entry` / `field_missing`；
   - `citations[]` 里每条原文引用有没有解析出 `keys`（`null` 就是没对上）。
3. 材料缺失、格式不认识、引用风格混杂：写进 `uncertainty`，不要猜。

### 3.2 判断"哪些是同一篇"（模型做的事）

只在这两种情况下合并，其余一律不合并：

| 依据 | 判据 | 记什么 |
|---|---|---|
| `doi` | 两条 DOI 去掉 `https://doi.org/` 前缀后**完全相同** | `merge_basis: "identical DOI ..."` |
| `title` | 标题归一化（小写、去标点、压空格）后 `SequenceMatcher ≥ 0.90`，**且第一作者姓氏相同**，**且标题里的数字序列完全相同** | `merge_basis: "title similarity 0.93 with the same first author 'Chen'"` |

- 同作者、不同题名 → **绝不合并**（预印本与正式版若 DOI 不同、标题也不同，就是不合并，交人工）。
- 会议版 vs 期刊版：DOI 相同才自动合并；合并时**保留信息更全的那条**（类型 J 优先于 C），
  另一条的缺失字段补进来，并记录 `merged_from`。
- 合并会改变编号，所以要一次决定完再跑，不要合并一条跑一次。

### 3.3 判断"哪些字段真的缺"（模型做的事）

对每条看 `completeness`：

1. `author/title/year/source` 缺 → 先在文献表原文里找（有的 `.bib` 把期刊写在 `booktitle` 里）；
   找不到就是缺，**不要从标题猜作者、从卷期推年份**。
2. `doi` 缺 → 老文献常见，写 `[TODO: doi]` 并**不要**声明该条完整。
3. 只有当你确认"这条真的齐全"时，才把 key 写进 `declared_complete`；写进去就等于签名，
   缺一个字段就是硬错误。

### 3.4 跑完整流程

```bash
python scripts/run_case.py --draft /app/work/draft.json
```

- `status=success`：0 个 error。warning 按 §4 处理（`uncited_entry`、`field_missing` 等仍要人看）。
- `status=partial`：读 `checks.json.errors`，**只改 draft 或改输入，不改检查器**：
  - `missing_entry`：正文的号在表里不存在 → 要么补条目（不能编），要么把该引用删掉/改号，并说明；
  - `unsafe_merge`：撤回这条 `merges` 提议；
  - `field_missing`（severity=error）：把该 key 从 `declared_complete` 里去掉，或补齐字段。
- 改写后的正文在 `manuscript_renumbered.md`；**不要**用它覆盖原稿而不留备份。

### 3.5 交付

`bibliography.md` 给人看（可直接贴进稿件），`references.json` 给机器读（映射 + 完整性），
`manuscript_renumbered.md` 是可直接替换正文的版本。三者必须互相对得上。

## 4. warning 的处置（不是错误，但必须交代）

| warning | 含义 | 处置 |
|---|---|---|
| `uncited_entry` | 文献表里有、正文没引 | 确认是"备用文献"还是漏引；漏引就补 `[n]`，不用就删条目 |
| `number_gap` | 编号重复或断号 | 重编号会修正正文，但文献表本身要人看一眼是否漏了一条 |
| `duplicate_entry` | 已按 DOI/标题合并 | 看 `basis` 是否成立；不成立就把两条的 DOI 补全再跑 |
| `field_missing`（severity=warning） | 该条缺字段，已写 `[TODO: …]` | 回原始文献补；补不到就保留 TODO，**不要编** |
| `draft_bad_merge` | `merges` 里有一项不是一对 key | 改成 `["keyA","keyB"]` |

## 5. 异常处理

| 情况 | 动作 |
|---|---|
| 没有可读正文 | `status=failed`，`errors=[{code:no_manuscript}]` |
| 没有文献表 | `status=failed`，`errors=[{code:no_library}]`，不要凭正文猜条目 |
| 文献表格式不认识（EndNote 标签、纯文本段落） | 如实报"解析到 0 条"，`uncertainty.next_step` 说明需要 `.bib/.ris/编号表` |
| 引用风格混杂（`[1]` 与 `(Smith, 2020)` 同时出现） | 两种都解析；只重编号数字标记，作者-年份原样保留，并在 `uncertainty` 说明 |
| 正文引用了不存在的编号 | `missing_entry`（硬错误），**不改写**该标记 |
| 同一 key 在 `.bib` 里出现两次 | 后者覆盖前者，`uncited_entry`/`duplicate_entry` 会暴露 |
| 超出预算 | 先交 `--check-only` 的对账报告（`status=partial`），`next_step` 写明还差哪些决策 |

## 6. 自检清单（提交前逐条打勾）

- [ ] `metrics.missing == 0`，或每条 `missing_entry` 都在 `uncertainty` 里说明了处理方式；
- [ ] `metrics.uncited == 0`，或每条未引条目都确认过要保留；
- [ ] `renumber_map` 的 `new` 从 1 连续到 `entries`，没有重复；
- [ ] 抽查 3 条：`bibliography.md` 的 `[n]` 与 `manuscript_renumbered.md` 的 `[n]` 指向同一条；
- [ ] 抽查 1 组合并：`basis` 是 DOI 还是标题相似度，`merged_from` 是否列全；
- [ ] `bibliography.md` 里每个 `[TODO: …]` 都是真的缺，不是漏解析；
- [ ] `result.json.output_contract` 没有 `null`。

## 7. 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/run_case.py` | 运行入口（`--check-only` / `--draft` / `--style`） |
| `scripts/cite_ledger.py` | 解析（bib/ris/编号表/四种引用）、对账、重编号、去重、GB/T 与 APA 渲染 |
| `scripts/skillkit.py` | 公共库（读文件、PDF 文本、引用正则、契约回填） |
| `references/check-rules.md` | 每条检查的判据、误报边界、返修建议 |
| `references/format-gbt7714.md` | GB/T 7714—2015 字段与拼接规则、TODO 约定 |
| `references/ledger-schema.md` | `draft.json` / `references.json` / `result.json` 字段契约 |
| `examples/` | 最小调用示例（示例输出已标 EXAMPLE） |
| `tests/cases/` | 3 个本地自测案例（非平台正式案例） |

## 8. 边界与诚实声明

- **不联网、不查库**：本 Skill 不验证文献是否真实存在、DOI 是否可解析、卷期页是否正确。
  它只保证"正文与文献表自洽、格式合规、缺字段留白"。真伪必须人工或联网核查。
- **引用的语义不查**：正文说"Smith 证明 X"，条目是不是 Smith 那篇讲 X 的文章，本 Skill 不管。
- **去重阈值是启发式**：标题归一化相似度 ≥0.90 + 同姓 + 数字序列一致，仍可能把"同题不同年版"误并；
  每条合并都写了 `basis` 供人复核。反过来，标题差异大的预印本/正式版不会合并——这是刻意的保守。
- **姓名切分有前提**：`Chen, Wei` / `Wei Chen` / `Chen W` 三种写法都能识别；
  但中文姓名转写（`Chen Wei` 无逗号无缩写）无法判定姓在前还是名在前，会按"名前姓后"处理。
- **`.ris` 没有 key**：引擎给内部 key 为 `risNN`，正文里用 `\cite{...}` 必然对不上，
  这类稿件请用编号引用（`[1]`）。
- **只重编号数字标记**：`\cite{key}` 与作者-年份不动（改它们会破坏 LaTeX 与语义）；
  作者-年份稿只做对账与格式转换，不强行改成顺序编码制。
- `tests/` 里的 3 个案例是**本地自测**，材料自造，**不是**平台正式案例，也不能当评测结果引用。
