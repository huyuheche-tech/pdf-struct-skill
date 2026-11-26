# 检查规则：每个 code 的触发条件、误报边界与返修

> 硬错误计 0 才可能 `success`。不要为了消错删断言、改证据原文或把两条合并成一条。

## 1. 硬错误

| code | 触发条件 | 返修 |
|---|---|---|
| `evidence_unresolved` | 无 evidence、或引文在指定段落/全文都找不到 | 从原文复制连续子串；换到正确段落 |
| `evidence_too_long` | evidence > 400 字符 | 截取承载该主张的那一句 |
| `triple_incomplete` | subject / predicate / object 任一为空 | 补齐三元组；object 写清数值与单位 |
| `predicate_invalid` | predicate 不在 7 个受控词表内 | 换成最接近的合法谓语，必要时改拆断言 |
| `not_atomic` | 含未拆 `;`、中文并列连词、或 `and` 连接两个主谓 | 拆成两条断言，各自带证据 |
| `condition_dropped` | 证据所在句含 under/when/only if/…，而 conditions 为空 | 把条件写进 conditions，保留原文限定 |
| `overbroad` | 断言含 all/always/never/every/所有/总是…，证据没有对应绝对表述 | 降级为 most/often/在…范围内，或改证据 |
| `duplicate_assertion` | 两条断言 text 归一化相似度 > 0.90 | 合并或改写为不同条件/不同对象 |
| `source_missing` | source_id 或 paragraph_id 为空 | 补来源标识与 `sNN.pMM` |

## 2. 误报边界（判错但属于真实问题，应改断言）

- **`and` 在名词短语里**（`precision and recall`）：不会触发；只有两侧都有谓语才算。
- **同段有多个 `when`**：只检查证据所在句，其他句子不牵连；但如果证据本身跨了条件句，
  就必须补 conditions——这说明证据取得太长。
- **`under` 出现在专名里**（`Underwood`）：词边界不匹配，不会触发。
- **`no significant difference`**：`no` 不在过宽词表内，不判 overbroad；它是否定，不是全称。
- **相似度高但信息不同**：例如只差一个数据集名，仍算重复；应改写为不同主张，
  而不是把阈值调高。

## 3. 不检查的东西（诚实边界）

- **断言是否科学上正确**：只验证「原文这么说、条件没丢、话没说满」，不验证实验设计。
- **三元组语义是否最优**：`has_property` 常能套用，但引擎不判断本体建模质量。
- **来源是否真实存在**：`source_id`/`doi` 只做非空与透传，不联网核验 DOI。
- **跨段证据**：不支持，也不假装支持；跨段会被判 `evidence_unresolved`。

## 4. 指标含义

| 指标 | 含义 |
|---|---|
| `assertions` | 断言条数 |
| `evidence_resolved` | 证据能在原文解析的条数 |
| `atomic` | 通过原子性检查的条数 |
| `overbroad` | 被判过宽的条数 |
| `duplicates` | 被判重复的条数 |

指标是诊断，不是分数；不要为让 `duplicates` 归零而删掉真实结论。
