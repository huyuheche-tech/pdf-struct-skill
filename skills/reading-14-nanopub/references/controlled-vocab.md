# 受控词表与断言原子性

## 1. 谓语词表（只能这 7 个）

| predicate | 含义 | 例子 |
|---|---|---|
| `supports` | 证据支持某结论/假设 | 消融结果 → 增益来自检索 |
| `contradicts` | 证据与某结论相反 | 复现失败 → 原结论 |
| `uses` | 方法/系统使用了某组件或数据 | 模型 → 稀疏注意力 |
| `compares` | 两组设置/方法被比较 | 方法 A → 方法 B |
| `has_property` | 主体具有某性质或数值结果 | 校准层 → 误差 6.3% |
| `measured_by` | 某量由某指标/仪器度量 | 校准质量 → ECE |
| `part_of` | 部分与整体关系 | 编码器 → 模型 |

- 大小写不敏感，导出时统一小写；
- `improves`、`reduces`、`causes`、`predicts` **不在**词表内：用一个 `has_property`
  把「降低到 6.3%」放进 `object`，或把它写成 `supports` 的结论；
- 词表是封闭的：加词等于改契约，需同步改 `PREDICATES`、本文件与 `SKILL.md`。

## 2. 原子性（not_atomic）

一条断言只能包含**一个可判定的主张**。以下判为不原子：

1. 含未拆分的 `;` / `；`；
2. 含中文并列连词 `并且 / 同时 / 以及 / 而且`；
3. `and` 连接两个独立主谓：`… lifts X and it costs Y`、`A reduces X and B improves Y`；
4. 一句话同时给「方法」和「结论」两个命题。

拆法示例：

```
差: The reranker lifts nDCG@10 to 0.358 and it costs 4.6 points to remove it.
好: a1 The reranker lifts nDCG@10 from 0.312 to 0.358.
    a2 Removing the reranker costs 4.6 points.
```

名词短语里的 `and`（`precision and recall`）不触发原子性错误。

## 3. 条件保留（condition_dropped）

原文出现以下线索时，断言必须写 `conditions`：

- 英文：`under`、`when`、`whenever`、`only if`、`in the setting of`、`conditional on`、`provided that`；
- 中文：`在…条件下`、`当…时`、`仅当`、`只有在`。

判定范围是**证据所在的那一句**，不是整段：同段其他句子的 `when` 不会误伤本条断言。
条件要写具体（`ImageNet-C severity 3`），不要写「某些条件」。

## 4. 过宽断言（overbroad）

断言句含 `all / always / never / every / everyone / everything` 或
`所有 / 全部 / 总是 / 从不 / 每个 / 一律 / 必然`，而**证据引文**里没有对应绝对表述时判错。

原文写 `in most cases`，断言写 `always` → 过宽。正确做法是保留 `in most cases`，
或把断言改成 `has_property: advantage in most cases`。

## 5. 证据引文规则

- 必须是所引段落的连续子串，压缩空白后逐字匹配；
- ≤400 字符；建议取**一句**，跨句会让条件范围与原子性都难以判定；
- 不要用省略号拼接两处文字；不要翻译原文；
- 段落号写错但全文能找到时，记 warning `evidence_elsewhere`，并如实把 `char_span` 置空。
