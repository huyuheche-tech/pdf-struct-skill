---
name: latex-build-doctor
description: 对 LaTeX 稿件做可复现的编译体检：括号/环境/数学模式配对、\cite 与 .bib 对账、\ref 与 \label 对账、表格列数与 & 数、booktabs 三线、caption、重复宏包，逐条给 file:line 与原行；--fix 只做重复 label 改名与未定义引用占位，有 TeX 时编译两遍并解析 log。当任务涉及"LaTeX 编译报错/投稿前体检/表格对不齐/引用未定义"时使用。
---

# LaTeX 写作与编译：静态体检 + 安全修复 + 可复现编译

## 0. 运行契约（先读这一节）

平台把本 Skill 装到 `/skills/weekly-skill`，案例在 `/input/case.json` + `task.md`，
成品写到 `/app/output/`。两条命令可直接复制：

```bash
# 第 1 步：静态体检 + 安全修复（产出 fixed.tex / diagnostics.json / report.md）
python scripts/run_case.py --case /input/case.json --input-dir /input --out /app/output --work /app/work --fix

# 第 2 步：把人工/模型修好的主文件放进 /app/work/draft.tex，再体检 + 修复 + 编译两遍
python scripts/run_case.py --case /input/case.json --input-dir /input --out /app/output --work /app/work --draft /app/work/draft.tex --fix --compile
```

可选参数：`--main main.tex` 指定主文件；`--no-compile` 关闭编译。
`case.json` 里写 `"compile": false` 等价于默认不编译（本地案例就是这样保证离线可复现的）。

`run_case.py` 会写：

| 文件 | 内容 |
|---|---|
| `report.md` | 人读的体检报告：每条问题 `file:line` + 原始行 + 修复建议 |
| `diagnostics.json` | `errors / warnings / fixes / patch_plan / compile / pre_fix` |
| `fixed.tex` | **仅 `--fix`**：只改了重复 label 与未定义 cite，其他一律不动 |
| `checks.json` | 与 `diagnostics.json` 同源的精简版（`errors`、`warnings`、`summary`） |
| `result.json` | 平台契约：`case_id` + `output_contract` 全部字段 + `status/evidence/uncertainty/sources` |

`result.json.main_result` 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `latex` | string | 交付的源码：有 `--fix` 时为 `fixed.tex`，否则为输入（或 draft）原文 |
| `checks` | object | `{errors[], warnings[], summary{}}` |
| `diagnostics` | object | 含 `fixes` 与 `patch_plan`，`patch_plan` 是不自动改的部分 |
| `metrics` | object | `{errors, warnings, compiled, cite_keys, labels, lines}` |
| `files` | object | 产出的文件名清单 |

**状态规则**：无可读 `.tex` → `failed`；没有 `--draft` → `partial`（`next_step` 写明要交什么）；
有 draft 且 0 个 error → `success`；有 draft 但仍有 error → `partial`。
**没有编译器时 `compiled` 只能是 `false`**，并把 `compiler_missing` 写进 `uncertainty`。

**预算**：64 次模型请求 / 900 秒 / 单回复 16384 token。体检本身不耗模型请求；
返修时一次只喂 `diagnostics.json` 里的一条错误（带 file:line 与原行），不要整篇重发。

**资源**：≤50 个 UTF-8 文本文件、单文件 ≤500KB、合计 ≤2MB、无符号链接；只用标准库。

## 1. 用途与适用条件

把一份 `.tex`（+ `.bib`）变成"**编译得通、改得对、交得可用、复现得了**"的稿件：
每条问题都能定位到 `file:line` 并回贴原行，修了什么、没修什么、为什么，全部留痕。

适用：单主文件（`\documentclass` 完整）的期刊/会议模板；有或没有 `.bib`；
本机有/没有 TeX 发行版（没有就只做静态检查，并明说没编译）。
不适用：多文件 `\include` 工程的结构性重构（只看主文件与直接引用的 `.bib`）；
`\write18`/外部工具链（如 minted、biber 后端）的运行时问题；版式审美。

## 2. 硬约束（评分点 → 保证方式 → 失败 code）

| 评分点 | 本 Skill 怎么保证 | 失败时 |
|---|---|---|
| **编译得通** | 括号/环境/`$` 配对；有 TeX 时 `pdflatex`/`latexmk` **两遍**，从 log 抽 `!` 与 `l.NN` | `unbalanced_brace` / `unbalanced_bracket` / `unbalanced_env` / `unbalanced_math` / `compile_error` |
| **改得对** | `\cite` key 必须在 `.bib`；`.bib` 未被引的条目报出来；`\ref` 必须有 `\label`；重复 label 单独报 | `cite_undefined` / `bib_unused` / `ref_undefined` / `label_duplicate` |
| **交得可用** | tabular 列声明与每行 `&` 数比对；三线表；table/figure 必须有 caption；重复宏包 | `table_column_mismatch` / `table_no_rules` / `caption_missing` / `package_duplicate` |
| **复现得了** | 每条诊断都带 `file:line` + 原始行；`--fix` 的每条改动写进 `fixes`，不自动改的写进 `patch_plan`；`compiled` 只在真实编译成功后为 `true` | 缺 `file/line/text` 即视为不合格；无编译器却写"编译通过"即造假 |

**`--fix` 的边界（只做两件安全事）**：

1. 重复 `\label{k}` → `\label{k-2}`、`\label{k-3}`，并把**该重复定义之后**的 `\ref{k}` 同步改名；
2. 未定义 cite key → `\cite{TODO-<key>}`，并列进 `fixes` 与 `cite_todo` 警告。

其余问题（表格列数、`$` 不配对、缺 caption）**只写 patch plan，不改正文**——自动改表格结构
会掩盖作者意图，也容易把"列少了"改成"数据丢了"。详见 `references/fix-policy.md`。

## 3. 操作流程

### 3.1 读输入，确认边界

1. 找主文件：`--main` > `case.json` 的 `main_tex` > 目录里最大的、不以 `fixed/draft` 开头的 `.tex`。
2. 找 `.bib`：输入目录下所有 `.bib` 都读入；**引用对账只在读到的 bib 范围内成立**，
   没有 bib 时所有 cite 都会报 undefined，此时应在 `uncertainty` 说明"未提供 bib"。
3. 读 `case.json` 的 `output_contract`，确认 `result.json` 要回填哪些字段（脚本自动映射）。

### 3.2 先跑静态体检

```bash
python scripts/run_case.py --case /input/case.json --input-dir /input --out /app/output --work /app/work
```

看 `report.md`：`errors` 是必须改的；`warnings` 是需人工判断的。逐条核对 `file:line` 与原始行——
如果原行与描述对不上，是你读错了文件（例如把 `draft.tex` 当成了 `main.tex`）。

### 3.3 自动修复只做安全的两类

```bash
python scripts/run_case.py ... --fix
```

`fixed.tex` 里只有 label 改名与 `TODO-` 引用占位。**打开 `fixes` 逐条核对**：
`\ref{sec:res-2}` 是不是真的该指向后一个同名 label？如果作者的意图是删掉重复 label，
就在 draft 里删，不要接受 `-2`。`TODO-` 必须换成真实文献，不能留在成品里。

### 3.4 人工返修（模型做的事）

按 `patch_plan` 逐条改，改完存成 `/app/work/draft.tex`，再跑第 2 步。
硬规则：

1. **不改检查器**去让错误消失；错误确实无法消除（例如 bib 不在手边），写进 `uncertainty`。
2. 表格列数不符时，先判断是列声明错了还是数据少了；只在**确认**是声明错时才改 `{lcc}`。
3. `$` 不配对时按语义补，不要把整段公式删掉。
4. 缺 caption 时补一句能描述该表/图的 caption，不要写 "Table."。

### 3.5 编译（有 TeX 才有）

`--compile` 会：把主文件与 bib 复制到 `/app/work/compile/`，用 `pdflatex` 两遍
（或用 `latexmk -pdf` 一遍），解析 `.log` 的 `!` 错误与 `l.NN` 行号，写成 `compile_error`。
**编译失败必须让 `status` 停在 `partial`**；没有编译器时 `compiler_missing=true`、
`compiled=false`，报告里明确写"未编译"。

### 3.6 交付

`report.md` 给人看，`result.json` 给平台读，`fixed.tex`（若有）是可直接编译的候选稿。
`main_result.latex` 放**最终交付的源码全文**，`metrics` 放计数，`evidence.anchors` 放
前 40 条 `file:line`，评委可据此逐条回查。

## 4. warning 处置表

| warning | 含义 | 处置 |
|---|---|---|
| `caption_missing` | table/figure 没有 `\caption` | 补一句描述性 caption；图表必须有题 |
| `table_no_rules` | 表格没有 booktabs 三线或 `\hline` | 换成 `\toprule/\midrule/\bottomrule`，不要只加上下框线 |
| `bib_unused` | `.bib` 有条目但正文没引 | 要么补引用，要么从 bib 删；投稿前必须清零 |
| `package_duplicate` | 同一宏包加载两次 | 删后一次；若选项不同，合并选项 |
| `cite_todo` | `--fix` 留下的 `TODO-key` 占位 | 必须换成真实文献，成品里不允许保留 |
| `compiler_missing` | 本机没有 pdflatex/latexmk | 报告里写"未编译"，不得声称编译通过 |

## 5. 异常处理

| 情况 | 动作 |
|---|---|
| 没有可读 `.tex` | `status=failed`，`checks.errors=[{code:no_material}]`，不编造诊断 |
| 没有 `.bib` 但正文有 `\cite` | 照报 `cite_undefined`，同时在 `uncertainty` 说明"bib 未提供，结论仅在已读 bib 范围内成立" |
| 多文件工程（`\input`/`\include`） | 只检查主文件与被 `\input` 的同目录文件；跨目录缺文件写进 `uncertainty` |
| 编码不是 UTF-8 | `skillkit.read_text` 依次尝试 utf-8-sig/utf-8/gb18030/latin-1；仍乱码则写 `encoding_suspect` |
| 编译超时 | 记 `compile_error`，`detail` 写 timeout，`compiled=false`，不重试到超预算 |
| 静态错误未清零 | 跳过编译（`compile.note=skipped: static errors remain`），先修静态错误 |
| 超出预算 | 先交静态体检结果（`status=partial`），`next_step` 写明剩余错误条数与行号 |

## 6. 自检清单（提交前逐条打勾）

- [ ] `report.md` 里每条 error 都有 `file:line` 和原始行；
- [ ] `metrics.compiled` 为 `true` 时，`compile.engine` 与 `runs` 都有值（真的跑过）；
- [ ] 没有编译器时，全文没有"编译通过"字样；
- [ ] `fixed.tex` 里的 `TODO-` 占位已全部替换，或明确写进 `uncertainty`；
- [ ] `patch_plan` 覆盖了所有未自动修复的 error；
- [ ] `output_contract` 没有 `null`；
- [ ] 抽查 2 条诊断：行号与原文对得上。

## 7. 文件说明

| 文件 | 作用 |
|---|---|
| `scripts/run_case.py` | 运行入口（分析 / 修复 / 编译 / 写 result.json） |
| `scripts/tex_doctor.py` | 静态检查、安全修复、日志解析 |
| `scripts/skillkit.py` | 公共库（读文件、材料发现、契约回填），勿改 |
| `references/check-rules.md` | 每条检查的判据、误报边界、返修建议 |
| `references/fix-policy.md` | `--fix` 做什么、不做什么、为什么 |
| `references/inputs-and-contract.md` | `case.json` / draft / 输出字段契约 |
| `examples/` | 最小调用示例（示例输出标 EXAMPLE） |
| `tests/cases/` | 3 个本地自测案例（**本地自测，不是平台正式案例**） |

## 8. 边界与诚实声明

- 本 Skill 是**静态检查器 + 编译驱动**，不是 TeX 解析器：`unescaped_special` 是
  高置信启发式（只报"数字后的 `%` 且后面还有成句文字"、"单词中间的 `_`"等），
  复杂宏定义里的特殊字符可能漏报或误报，结果里一律标为 error 并给出原文，供人复核。
- **不做**：版式审美、参考文献格式（用 `citation-ledger`）、语言润色（用 `academic-polish-ledger`）、
  图片转矢量、模板适配。
- `--fix` 只做两类安全改名；**不自动改表格、公式、正文语义**。
- 没有 TeX 发行版时**绝不**声称编译通过；`compiled=false` + `compiler_missing=true` 是本 Skill 的
  正常输出之一，不是失败。
- `tests/cases/` 里的 3 个案例是**本地自测，不是平台正式案例**（broken / clean / ctex 中文短文），
  材料全部自造，不能拿来冒充评测分数。
