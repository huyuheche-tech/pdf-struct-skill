# 术语表策略

## 1. 三种来源，优先级从高到低

1. **案例自带术语表**（`glossary.csv` / `glossary.json` / `case.json.glossary`）：必须执行，不得替换。
2. **领域惯例**：方法名、数据集名、指标名按原文保留（`ResNet-50`、`ImageNet`、`BLEU`），
   首次出现给中文解释，之后统一用原文。
3. **自动候选**：从标题、摘要、图注抽高频多词短语与缩写；候选只用于提示，不是译名标准。

## 2. CSV 格式

```csv
source,target,note
attention mechanism,注意力机制,
residual connection,残差连接,
F1 score,F1 值,指标名保留 F1
```

- `source` 大小写不敏感匹配；
- 同一 `source` 出现两行且 `target` 不同 → 冲突，取出现次数多者，另一条写进
  `uncertainty.human_review`，**不自动合并**；
- `target` 为空 → 该条只算候选，不参与强制校验。

## 3. 全篇一致性判据

对每条锁定术语，按 `zone`（title / abstract / body / caption / reference）统计：

- `used`：该区域内出现该术语的段数；
- `ok`：译文中使用了锁定译名的段数；
- `consistent`：该区域 `ok == used`。

`glossary_matrix` 出现 `0/n` 说明整段没用锁定译名，必须返修；出现 `n-1/n` 说明只有一段漂移，
按段号定位后改那一段，不要改术语表。

## 4. 什么情况可以合法地不统一

- 原文本身用了两个不同概念（如 `accuracy` 与 `precision`），中文不能都译成「准确率」；
- 术语在参考文献标题里（`reference` 区域），保持原样或按该文献的既有译名；
- 直接引语中的术语。

这三种情况在 `checks.json` 里仍然是 `term_missing`，但可在 `uncertainty.human_review`
说明「该段属于例外」，不要为了消错而误译。
