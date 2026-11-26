---
name: methods-parameter-ledger
description: 从 config.json/config.yaml/train.log/notes 抽取参数台账（name/value/unit/source），据此写方法与实验章节并逐项校验：正文每个数字可溯源、六类要素齐全、复现清单不缺项、基线与数据集写清楚。当任务涉及"写方法章节""写实验设置""参数对不上""复现清单""审方法部分"时使用。
---

# 方法与实验章节：参数台账 + 数字溯源

## 0. 运行契约（先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，案例在 `/input/case.json` + `task.md`，成品写到 `/app/output/`。

```bash
# 第 1 步：把 config / log 摊平成参数台账
python scripts/run_case.py --plan-only

# 第 2 步：把方法稿写进 /app/work/draft.json，再校验并出成品
python scripts/run_case.py --draft /app/work/draft.json
```

`run_case.py` 会写：

| 文件 | 内容 |
|---|---|
| `params.json` | 每条参数 `name/value/unit/source(file:line)`，来自 json/yaml 递归展开、log 的 `key=value`/`key: value`/`--flag value` |
| `methods.md` | 方法成稿 + 文末参数台账表 |
| `gaps.json` | `repro_gap`、`todo_placeholder` 等"缺失但不一定是错误"的项，附八项复现清单状态 |
| `checks.json` | `errors`（硬失败）、`warnings`、`gaps`、`summary`、`metrics` |
| `result.json` | 平台契约：`case_id` + `output_contract` 全部字段 + `status/evidence/uncertainty/sources` |

**draft.json 格式（接受两种）**

```json
{"methods": "方法与实验章节全文（Markdown 或纯文本）"}
```

```json
{"methods": "...",
 "params": [{"name": "optimizer.lr", "value": "0.001", "unit": "", "source": "config.json:5"}]}
```

规则：正文用 `[TODO: ...]` 标未确认内容，会被记为 gap 而不是假数字；draft 自带 `params` 时只用于补充，
正文里的数字仍要能在材料或台账里找到。

**预算**：64 次模型请求 / 900 秒 / 单回复 16384 token。建议先 `--plan-only`，按"步骤 / 设置 / 数据 / 对照 /
复现"分块写，每块带上对应参数行，不要一次塞整份 log。

**资源**：≤50 个 UTF-8 文本文件、单文件 ≤500KB、合计 ≤2MB、无符号链接；只用标准库，不联网。

## 1. 用途与适用条件

把配置文件、训练日志和实验笔记，变成一段**每个数字都有来源、复现清单逐项可查**的方法章节。

适用：有 `config.json` / `config.yaml` / `train.log` / `notes.md` 中任意一种或多种；中英文均可；
已有 draft 需要体检；也可以只跑 `--plan-only` 拿参数台账交给写作模型。

不适用：没有任何配置或日志却要求"补全实验参数"；需要真正跑实验验证结果（本 Skill 不执行训练）；
纯语言润色（用「学术语言润色」Skill）。

## 2. 四个硬约束（评分点逐条对应）

| 评分点 | 本 Skill 怎么保证 | 失败 code |
|---|---|---|
| **写得全** | 六类要素（步骤/实验设置/参数/数据集/对照/复现与限制）各至少命中 1 个关键词 | `category_missing` |
| **写得准** | 正文每个数字必须出现在参数台账或材料原文；`[TODO: ...]` 记 gap 不算数字 | `number_unsourced` |
| **做得着** | 对照实验必须写基线名称 + 同预算条件；数据集必须写名称 + 版本/规模 + 划分 | `baseline_underspecified` / `dataset_underspecified` |
| **说得住** | 八项复现清单（seed、数据版本、split、batch size、学习率、epochs、硬件/框架版本、运行命令）逐项核对；正文声称 reproducible 时缺项升级为 error | `repro_gap` |

**不得**为了让检查变绿而改材料里的参数、删掉没写清的数据集、把"可复现"改成不提。这些正是评委要看的失败模式。

## 3. 操作流程

### 3.1 读输入，先看台账

1. `case.json` 可能给出 `title / materials / output_contract`；材料可能是 `config.json`、`config.yaml`、
   `train.log`、`notes.md`。**按实际文件读，不要按文件名猜内容。**
2. 跑 `--plan-only`，看 `params.json`：
   - 嵌套配置是否摊平成 `a.b.c`；
   - log 里的 `lr=0.001`、`--batch_size 64` 是否进来了；
   - 每条是否有 `source`（`config.json:5` 这种）。
3. 参数缺失或两份材料冲突时，先停下来核对，不要用"看起来合理"的默认值填。

### 3.2 按六类要素搭骨架

| 要素 | 写什么 | 关键词示例 |
|---|---|---|
| 步骤 | 数据怎么进、模型怎么训、怎么选 checkpoint | first / then / finally、首先 / 然后 / 最后 |
| 实验设置 | 硬件、框架与版本 | GPU、PyTorch 2.1.0 |
| 参数 | 学习率、批大小、epochs、seed、weight decay | learning rate、batch size、随机种子 |
| 数据集 | 名称 + 版本/规模 + 划分 | GLUE、version 2.0、80% train |
| 对照 | 基线名称 + 同预算条件 | BERT-base、same training budget |
| 复现与限制 | 复现命令、单语言/单数据集等限制 | reproduce、limitation |

### 3.3 写数字的规矩

1. 先从 `params.json` 抄，不要凭记忆写；`0.001` 不要写成 `0.01`，`64` 不要写成 `128`。
2. 正文没把握的数字写 `[TODO: 待确认 batch size]`，它会进 `gaps.json`，不会被当成已证事实。
3. 数据集版本、split 比例、基线预算都要落在正文里，不能只留在 config 里。
4. 声称 "fully reproducible" 之前，先把八项复现清单补齐；否则 `repro_gap` 会从 gap 升级成 error。

### 3.4 校验与返修

```bash
python scripts/run_case.py --draft /app/work/draft.json
```

- `status=success`：0 个 error。`gaps.json` 仍可能有 `repro_gap` / `todo_placeholder`，按 §4 处理。
- `status=partial`：读 `checks.json.errors`，只改 draft，不改检查器；改完重跑。
- 改参数时先看 `params.json` 的 `source`，确认自己改的是正文还是材料。

### 3.5 交付

`methods.md` 给人看；`result.json` 给平台读。`result.json.main_result` 里有 `methods`、`tables`（参数台账）、
`checks`、`metrics{params,numbers_sourced,n_numbers,coverage,repro_items}`，`output_contract` 由
`skillkit.write_result` 自动回填。

## 4. gap / warning 的处置（不是错误，但必须交代）

| 项 | 含义 | 处置 |
|---|---|---|
| `repro_gap`（gap） | 八项复现清单缺项，正文未声称可复现 | 能补就补；补不了在 `uncertainty.gaps` 如实列出 |
| `repro_gap`（error） | 正文声称 reproducible 但清单缺项 | 补 seed / 命令 / 版本，或删掉"可复现"的表述 |
| `todo_placeholder`（gap） | 正文有 `[TODO: ...]` | 交付前尽量清零；保留时在 `uncertainty` 说明 |
| 未溯源数字（error） | 正文数字不在材料里 | 改回材料值，或把材料补进输入 |

`warnings` 通常为空；`gaps` 不影响 `status`，但必须在 `uncertainty.gaps` 里逐条交代，不能藏起来。

## 5. 异常处理

| 情况 | 动作 |
|---|---|
| 没有任何可读材料 | `status=failed`，`checks.errors=[{code:no_material}]`，不写假参数 |
| config 是空文件 / 解析失败 | 台账为空，正文数字全部 `number_unsourced`；先修材料，不要手填 |
| 两份材料参数冲突（config 0.001、log 0.01） | 以 config 为准并在 `uncertainty` 列出冲突，不要静默选一个 |
| log 行格式特殊（JSON lines、wandb 表） | 先转成 `key=value` 或 `key: value`；转不了就只作原始材料供溯源 |
| 数据集版本缺失 | 记 `dataset_underspecified`；不要把"最新版"当版本 |
| 正文声称 reproducible 但缺命令 | `repro_gap` 升级为 error；补命令或删掉该表述 |
| 超出预算 | 先交已写段落（`status=partial`），`next_step` 写剩余要素 |

## 6. 自检清单（提交前逐条打勾）

- [ ] `params.json` 覆盖正文用到的每个参数，且每条有 `source`；
- [ ] 正文每个数字都能在台账或材料里找到，`[TODO]` 已清零或已交代；
- [ ] 六类要素各有至少一句话，不靠标题凑数；
- [ ] 数据集写了名称 + 版本/规模 + 划分；
- [ ] 对照实验写了基线名称 + 同预算条件；
- [ ] 八项复现清单逐项核对；声称 reproducible 时没有缺项；
- [ ] `result.json` 的 `output_contract` 字段没有 `null`。

## 7. 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/run_case.py` | 运行入口（两阶段） |
| `scripts/methods_ledger.py` | 参数抽取、数字溯源、六类覆盖、复现清单、基线与数据集校验 |
| `scripts/skillkit.py` | 公共库（读文件、PDF 文本、契约回填） |
| `references/check-rules.md` | 每条检查的判据、误报边界、返修建议 |
| `references/draft-schema.md` | `draft.json` / `params.json` / `gaps.json` / `result.json` 字段契约 |
| `references/param-extraction.md` | json/yaml/log 的展开规则与单位推断 |
| `examples/` | 最小调用示例（示例输出已标注 EXAMPLE） |
| `tests/cases/` | 3 个本地自测案例（非平台正式案例） |

## 8. 边界与诚实声明

- 本 Skill **不判断方法写得好不好**，只保证"六类齐、数字有源、基线/数据集写清、复现清单可查"。
- 它**不执行训练、不推断缺失参数、不补实验**；材料没有的参数只能写 `[TODO]` 或留空。
- 单位推断只覆盖常见后缀（`%`、`GB`、`ms` 等）与常见无量纲键（`lr`、`batch_size`、`epochs`、`seed`），
  推不出时留空，不猜。
- 本地 `tests/` 里的 3 个案例是自造的管线测试，**不是**平台正式案例，也不能拿来冒充评测结果。
