# `--fix` 策略：只做两件不会改变作者意图的事

自动改写 LaTeX 正文的风险在于：机器不知道"这是笔误"还是"这是作者想要的"。
所以 `--fix` 只做两类**可逆、可核对、语义唯一**的修补，其余全部落进 `patch_plan`。

## 做：重复 label 改名 + `\ref` 同步

`\label{sec:res}` 出现两次时，LaTeX 只会记住最后一个，前面的 `\ref` 全部指错。

规则：

1. 第一次出现的 key 保持不变；
2. 第 n 次（n≥2）出现改成 `key-n`（若已存在则继续 `key-n+1`）；
3. 该重复定义**之后**的 `\ref{key}` 同步改成 `\ref{key-n}`；定义之前的 `\ref` 不动
   （它更可能指向第一个 label）。

这是**启发式**：如果作者的意图是"删掉重复 label"，`-2` 就是错的。所以每条都进 `fixes`，
`report.md` 里逐条列出"第几行把什么改成了什么"，要求人打开 `fixed.tex` 复核。

## 做：未定义 cite key 变占位

`\citep{unknown2021}` 在 bib 里找不到时，改成 `\cite{TODO-unknown2021}`：

- 编译不再因为 undefined citation 报错；
- 但**成品里不允许出现 `TODO-`**，它会被记成 `cite_todo` 警告，逼作者补真实文献。

这样既保住"编译得通"，又不伪造一条参考文献。

## 不做：表格列数

`{lcc}` 但某行有 4 个 `&`，可能是：

- 列声明漏了一个 `c`（改声明）；
- 那行多写了一个 `&`（删 `&`）；
- 数据本身多了一列（要补表头）。

三种修法结果完全不同。自动改任何一种都是替作者做实验数据层面的决定，
所以只报 `table_column_mismatch` + patch plan。

## 不做：`$` 配对

缺一个 `$` 时，"补在哪"决定公式覆盖哪些词。自动补会把正文吞进数学模式，
产生更难查的错误。只报 `unbalanced_math` 并给出最后一个 `$` 的行号。

## 不做：缺 caption / 三线表 / 重复宏包

- caption 需要读懂图表内容，机器写出来的 "Table." 是噪声；
- 三线表涉及 `\multicolumn` 与列宽，自动替换容易破坏对齐；
- 重复宏包如果有不同选项，删哪一个要看模板要求。

这三类只给 warning + patch plan。

## 幂等性

对 `fixed.tex` 再跑一次 `--fix` 不应再产生新的改名：重复 label 已唯一，
`TODO-` key 会被跳过，所以 `fixes` 为空。测试里用这一点防止"越修越乱"。

## 审计字段

```json
{"code": "label_duplicate", "file": "main.tex", "line": 49,
 "action": "rename \\label{sec:res} -> \\label{sec:res-2}", "auto": true}
```

`fixes` 只记**实际发生的替换**；`patch_plan` 记**建议但未执行**的修改，
字段是 `{code, file, line, target, patch}`。
