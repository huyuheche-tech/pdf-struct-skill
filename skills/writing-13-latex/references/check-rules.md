# 检查规则：判据、误报边界、返修建议

每条诊断都带 `code / severity / file / line / text / detail / hint`。
`text` 是**原始行**（不是去注释后的行），方便直接回贴到编辑器。

## 1. 结构配对

| code | 级别 | 判据 | 误报边界 |
|---|---|---|---|
| `unbalanced_brace` | error | 去掉注释后扫描 `{`/`}`；`\{` `\}` 视为转义跳过 | 花括号在 `\verb|...|` 或 verbatim 环境里时仍会被计入——遇到就人工核对 |
| `unbalanced_bracket` | error | 同上，扫描 `[`/`]`，跳过数学模式内的方括号 | 数学区间 `[0,1)` 在数学模式内，不会误报；正文里的 `[12]` 数字引用会配对 |
| `unbalanced_env` | error | `\begin{x}` / `\end{x}` 用栈匹配，报不匹配、无 begin 的 end、未闭合的 begin | `\begin` 出现在注释里不参与（注释已剥离） |
| `unbalanced_math` | error | `$` 总数为奇数，或 `\[` 与 `\]` 数量不等 | `\$` 不计；`$$` 计两个；跨行公式按全文计数，不按行 |

## 2. 引用与标签

| code | 级别 | 判据 | 误报边界 |
|---|---|---|---|
| `cite_undefined` | error | `\cite/\citep/\citet/\citealp/...` 的每个 key 必须在读到的 `.bib` 里 | `TODO-` 开头的占位 key 不报（它们是 `--fix` 的产物，改由 `cite_todo` warning 跟踪） |
| `bib_unused` | warning | bib 条目 key 未在正文任何 cite 命令中出现 | 仅统计已读到的 bib；多 bib 合并时按 key 去重 |
| `ref_undefined` | error | `\ref/\eqref/\autoref/\cref/\pageref/\nameref` 的 key 必须有 `\label` | 指向 `\label` 定义在别的 `.tex`（`\input` 文件）时会误报，需在 `uncertainty` 说明 |
| `label_duplicate` | error | 同一 key 第二次及以后出现 | 报每一次重复，`detail` 给出首次行号 |

## 3. 表格

| code | 级别 | 判据 | 误报边界 |
|---|---|---|---|
| `table_column_mismatch` | error | `\begin{tabular}{spec}` 解析出的列数 ≠ 该行 `&` 数 + 1（`\multicolumn{n}` 按 n 计） | 列声明支持 `l c r X S Y p{m} m{b} *{n}{...} @{...}`；`\multicolumn` 跨行合并的复杂表可能误报，报出来后人看一眼 |
| `table_no_rules` | warning | table 环境里有 tabular 但没有任何 `\toprule/\midrule/\bottomrule/\hline` | 纯图片表、`\begin{tabular}` 在 `\resizebox` 里的情况按同一规则处理 |
| `caption_missing` | warning | table/figure 环境块内没有 `\caption` | `\captionof` 不识别，会误报，人工确认 |

列数解析示例：`{lcc}` → 3；`{|l|c|}` → 2（竖线不算列）；`{p{3cm}*{2}{c}}` → 3。

## 4. 正文特殊字符

| code | 级别 | 判据 | 误报边界 |
|---|---|---|---|
| `unescaped_special` | error | 只报高置信四种：`%` 前是数字且后面还有 ≥2 个英文词；单词中间的 `_`（`model_config`）；tabular/数学环境外的 `&`；宏定义行之外的 `#` | 命令参数（`\label{}`/`\cite{}`/`\includegraphics{}` 等）与 `\verb` 内不报；中文里 `95%` 若前面是数字也会报——这正是要修的情况 |

普通注释行（`%` 在行首或前面是空格）**不报**：那是合法注释，不是漏转义。

## 5. 宏包与编译

| code | 级别 | 判据 |
|---|---|---|
| `package_duplicate` | warning | 同一 `\usepackage` 名字第二次加载 |
| `compile_error` | error | `pdflatex`/`latexmk` 非零退出，或 log 里有 `!` / `file.tex:NN:` 且不是 warning |
| `compiler_missing` | warning | PATH 上没有 `pdflatex` 也没有 `latexmk`；此时 `compiled=false` |

`compile_error` 的行号优先取 `-file-line-error` 的 `file:line:`，否则取 `!` 之后最近的 `l.NN`。
同一个（行号, 消息）只报一次，最多 20 条。

## 6. 返修顺序建议

1. 先修 `unbalanced_env` / `unbalanced_brace`——它们会让后面所有行号错位；
2. 再修 `cite_undefined` / `ref_undefined`（`--fix` 能处理 cite 占位）；
3. 再修 `table_column_mismatch`（要人判断是声明错还是数据缺）；
4. 最后补 `caption_missing` / 三线表；
5. 以上清零后再 `--compile`，否则编译日志会被前置错误淹没。
