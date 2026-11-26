# 检查规则与误报边界

每条检查都对应 `checks.json.errors / warnings` 里的 `code`。**错误不可静默忽略**：
要么改稿子，要么在 `result.json.uncertainty` 写明为什么消不掉。

## 1. 硬错误（`status=partial`）

| code | 判据 | 常见误报 | 正确处置 |
|---|---|---|---|
| `number_missing` | 该句源文数字多重集里有、改稿没有 | 源文用汉字数字「三个」，改稿写成 `3` 会同时触发 `number_added` | 数字原样保留；中文数词可保留汉字 |
| `number_added` | 改稿多出源文没有的数字 | 把「一边」拆成 `1` 边；新增了年份 | 删掉多出来的数字，或确认为必要后写进 `human_review` |
| `number_changed` | 同一句里缺失数与新增数一一对应 | 把 `18.4%` 写成 `18.40%`（数值等价但字符不同） | 逐字保留排版形式，不做等价改写 |
| `citation_changed` | 该句引用标记集合变了（丢或增） | 作者-年份改成纯括号编号（跨风格改写） | 保持原风格；换风格是"引用管理"Skill 的事，不是润色 |
| `hedge_strengthened` | 源句有 `may/might/could/suggest/indicate/likely/possibly`，改句出现 `prove/demonstrate/show that/confirm/establish` 且不再留 hedge | 源句本身同时有 hedge 与 `demonstrate`，而改稿只是删了 hedge | 保留 hedge；确实要断言，先确认有证据，并在 `human_review` 说明 |
| `negation_changed` | 否定极性翻转 | 「不同/不仅/无论/不停」被当成否定（词表已排除这几个） | 别把「不显著」改成「显著」；这会把结论改反 |
| `term_missing` | 源句出现术语表里的词，改句没用锁定写法 | 该句是直接引语，或参考文献标题里的术语 | 改稿用锁定写法；例外写进 `human_review` |
| `edit_unexplained` | 台账条目没有 `reason`；或某句改了但没有台账条目（自动补的条目没有 reason） | 只交了 `edited_text`（引擎会补齐台账但补不出理由） | 每条改动都写一句"为什么"，不要写"优化表达"这种空话 |
| `edit_bad_type` | `type` 不在 `grammar/term/tone/clarity` 内（含缺失） | 写了 `spelling`、`style` | 归到四类里最近的一类 |
| `edit_unanchored` | 台账 `original` 在原文里找不到 | `original` 抄自改稿而不是原文；跨句摘录 | 从 `material.md` 里复制原句片段 |
| `residual_grammar` | 改稿里仍有 a/an 错、句首 `It/He/She`+动词原形、行内双空格、句首小写、`et al` 缺句点 | `an MRI` / `a university` 这类读音规则例外已排除；`e.g.`、`i.e.`、`pH`、`mRNA` 开头的小写已白名单 | 按 `rule` 字段提示改；`rule` 见下表 |

`residual_grammar.rule` 取值：`a_an` / `sva` / `double_space` / `lowercase_start` / `etal_period`。

## 2. 警告（可交付，但必须交代）

| code | 判据 | 处置 |
|---|---|---|
| `hedge_weakened` | 源句是断言，改句变弱 | 确认没有把结论改小；必要时改回 |
| `alignment_gap` | 有一句在另一边没有对应（句子被合并/拆分/增删） | 尽量一句对一句；确需合并就在台账登记 |
| `edit_noop` | `original` 与 `edited` 相同却写了理由 | 删掉该条 |
| `edit_duplicate_id` | 台账 id 重复 | 换唯一 id |

## 3. 刻意的取舍（宁可漏报，不误报）

- 主谓一致只查句首 `It/He/She` + 动词原形。`made it work`、`let it run` 这类不会误报，
  但句中真正的主谓错误也就查不到。
- a/an 只查"字母开头且不含数字"的普通单词；缩写（`MRI`、`LLM`）与读音例外（`hour`、`university`、`one`）跳过。
- 句首小写只查 `.!?` + 空格 + 小写字母，且排除 `e.g.` `i.e.` `et al.` `Fig.` `Eq.` 之后的续写。
- 双空格只查"非空白 + ≥2 空格 + 非空白"，行首缩进不报（Markdown 列表会缩进）。
- 句级对齐用 `difflib` 在归一化（压空白、去首尾）之后的句子上做，**标点或大小写改动不会被判成"删句"**。

## 4. 检查不到的东西（必须写进 uncertainty）

- 逻辑是否更清楚、因果是否成立、指代是否明确；
- 是否符合目标期刊的语体（本 Skill 没有期刊模板）；
- 术语是否符合该领域惯例（只保证与你给的术语表一致）；
- 改稿是否引入了新的事实错误（只保证数字/引用/否定/强度没变）；
- 图表内文字、公式排版。

以上写在 `result.json.uncertainty.note`，不假装覆盖。
