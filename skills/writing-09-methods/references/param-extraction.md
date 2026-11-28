# 参数抽取规则

引擎只做确定性抽取，不推断缺失值。

## 1. JSON：递归摊平

```json
{"optimizer": {"lr": 0.001}, "training": {"batch_size": 64}}
```

→

```
optimizer.lr = 0.001
training.batch_size = 64
```

- 列表用下标：`augment.ops[0] = flip`。
- 布尔/`null` 不写入台账（`true/false/null` 跳过）。
- `source` 取叶子键在原文中首次出现的行号，写作 `config.json:5`。

## 2. YAML：缩进栈

只支持简单 `key: value` 与缩进嵌套：

```yaml
training:
  batch_size: 64
  epochs: 40
```

→ `training.batch_size = 64`、`training.epochs = 40`。

- 行内注释、空行、`key:` 后无值（作为父节点）都按规则处理。
- 不支持锚点、多文档、流式集合；遇到就当普通字符串。

## 3. 日志：三种写法

| 写法 | 例子 | 解析为 |
|---|---|---|
| `--flag value` | `--batch_size 64` | `batch_size = 64` |
| `key=value` | `lr=0.001` | `lr = 0.001` |
| `key: value` | `epoch: 3` | `epoch = 3`（仅当该行没有 `=` 时启用，避免重复） |

- 同一行多个键值都会收；时间戳 `10:00:00` 因键名不以字母开头被跳过。
- 只对 `*.log`、以及内容像日志的 `*.txt` 启用（连续 ≥3 行含 `=` 或 `--flag`）；`*.md` 一律不当日志，避免把散文误当参数。

## 4. 单位推断

按顺序：

1. 值后缀命中常见单位 → 用该单位：`% / GB / MB / TB / KB / ms / s / min / h / bp / kDa / Da`。
2. 键名属于无量纲集合 → 空字符串：`lr / learning_rate / weight_decay / dropout / batch_size /
   epochs / seed / warmup / steps / length / layers / heads`。
3. 都推不出 → 空字符串，不猜。

示例：`optimizer.lr = 0.001` → 单位空；`memory = 32GB` → `GB`；`dropout = 0.1` → 空。

## 5. 去重与溯源

- 相同 `(name, value)` 只保留第一条，`source` 指向首次出现。
- 同名不同值不自动合并；它们会作为两条并存，正文数字只要命中任一条即可溯源，
  但交付时应在 `uncertainty` 里指出冲突。
