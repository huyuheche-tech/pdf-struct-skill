# 检查规则与误报边界

每条检查都对应 `checks.json.errors/warnings` 里的 `code`。**错误不可静默忽略**：要么改译文，
要么在 `result.json.uncertainty` 写明为什么消不掉。

## 1. 硬错误（status=partial）

| code | 判据 | 常见误报 | 正确处置 |
|---|---|---|---|
| `missing_segment` | draft 缺少 `plan.json` 里的段号 | 无 | 补译该段；原文为空则写 `【空段】` |
| `duplicate_segment` | 同一 id 在 draft 出现两次 | 模型把两段合并后又写了一遍 | 拆回两段，各给一个 id |
| `number_missing` | 源段数字多重集 ⊄ 译文数字多重集 | 中文数词（「三组」）被写成 `3` 会触发 `number_added`，不是本条 | 阿拉伯数字原样保留；「三」这种原文数词可保留汉字 |
| `citation_missing` | 源段引用标记在译文中找不到 | 作者-年份被本地化为「等」 | 保留第一作者+年份，或原样保留 `[12]` |
| `formula_changed` | `$...$`/`\(...\)`/`equation` 环境不是逐字出现 | 公式被排版成图片 | 原样保留；无法保留时标 `【公式见原文】` 并记 warning |
| `term_missing` | 锁定术语在该段出现，但译文没用锁定译名 | 术语只在参考文献标题里 | 例外写进 `human_review` |
| `negation_lost` | 源段有否定词，译文没有 | 中文用「未」被误判？不会，`未` 在词表里 | 补否定；不要把 `fail to` 译成「成功地」 |

## 2. 警告（可交付，但必须交代）

| code | 判据 | 处置 |
|---|---|---|
| `number_added` | 译文多出数字 | 检查是否把「一/二」写成阿拉伯数字 |
| `citation_localised` | 引用标记形态变化但作者/年份还在 | 可接受 |
| `negation_added` | 译文多出否定 | 检查是否误译 |
| `hedge_lost` | 源段有 `may/suggest/indicate/likely`，译文没有对应弱化词 | 改译文或列入人工确认 |
| `length_outlier` | 译文字符数/源文字符数 <0.25 或 >3.0 | 检查漏译或扩写 |
| `back_translation_diverges` | 回译与原文相似度 <0.45 | 只作为漏译线索，不作为质量结论 |

## 3. 检查不到的东西（必须写进 uncertainty）

- 译名是否符合某期刊的官方译法；
- 长句的逻辑关系是否保持（只查否定/限定极性，不查因果/让步）；
- 图表内文字（本 Skill 不解析图片）；
- 参考文献条目本身的真伪。

这四项在 `result.json.uncertainty.note` 里明确声明，不要假装覆盖。
