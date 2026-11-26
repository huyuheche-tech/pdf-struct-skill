# 引言检查规则与返修边界

所有检查都是确定性的，只看 draft 与材料/证据表，不评价文笔。

## section_missing

- 触发：`sections` 里 `background / related_work / gap / contributions` 任一为空。
- 通过：四段都有非空内容；`contributions` 是至少 1 条的非空列表。
- 误报边界：只有标题没有正文也算空；空白字符不算内容。
- 返修：补写该段，或把内容拆进正确的段，不要为了凑数复制别段。

## citation_missing

- 触发：某段既没有任何引用标记，也没有在 `author_judgment` 里声明该段。
- 通过：段内出现 `[key]`、`\cite{key}` 或 `(Author, year)` 之一；或 `author_judgment` 含该段名。
- 误报边界：`contributions` 默认是作者判断，可在 `author_judgment` 里声明；背景/相关工作/空白不建议这样绕。
- 返修：补真实引用；无引用可补时，才用 `author_judgment`，并在 `uncertainty` 说明。

## claim_unsupported

- 触发：draft 某段里的某个数字（去掉引用标记后）不在 `evidence.json` 的数字集合里。
- 通过：每个数字都能在证据表某条句子的 `numbers` 里找到。
- 误报边界：引用里的年份、`[3]` 这类编号会先被剥离；单位写法差异（`18.4 %` vs `18.4%`）按去空格后比较。
- 返修：改回材料里的数字，或把含该数字的材料句子补进输入后重跑；不要改检查器。

## contribution_unbound

- 触发：第 i 条贡献没有对应的 `contribution_evidence`，或 `quote` 不能在材料里逐字解析。
- 通过：`contribution` 从 1 连续覆盖所有贡献；每条 `quote` 经 `skillkit.check_quote` 命中。
- 误报边界：`quote` 可以是从句，但必须连续；改时态、单复数、标点都可能失配。
- 返修：换成材料原句，或删掉这条无法支撑的贡献。

## gap_unsupported

- 触发：`gap` 段非空，但不同引用少于 2 条。
- 通过：`gap` 段至少 2 个不同 key/作者-年份。
- 误报边界：同一篇文献重复引用只算 1 条；数字编号 `[3]` 与 key `[liu2019]` 都算引用标记。
- 返修：补一篇真正指出空白的文献；不要把同一篇拆成两个写法。

## grouping_thin

- 触发：`groups` 少于 2 组，或某组 `label` 为空、`works` 为空。
- 通过：≥2 组，每组有具体标签和至少 1 个 work。
- 误报边界：组标签写"相关研究"不算空，但建议写具体类别；引擎只查非空，不查语义。
- 返修：按"这一类做了什么"重新分组，不要把一组硬拆成两组。

## citation_unknown

- 触发：给定了 `.bib`/`.json` 文献库，但正文或 groups 里的 key 不在库中；作者-年份对不上库里的姓+年份。
- 通过：所有 key 都能在库中解析。
- 误报边界：没有文献库时不会报此错，只记 `citation_unverified` warning。
- 返修：改 key 拼写、补库条目，或删掉无法核实的引用；**不要伪造条目**。
