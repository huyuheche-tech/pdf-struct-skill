# Example: methods text backed by a parameter ledger

## Input

`examples/input/` contains `case.json`, `config.json`（嵌套训练配置）, `train.log`, `notes.md`
和 `draft.json`（方法全文）。

```bash
python scripts/run_case.py --case examples/input/case.json --input-dir examples/input \
    --out /tmp/ex --work /tmp/ex-work --plan-only
python scripts/run_case.py --case examples/input/case.json --input-dir examples/input \
    --out /tmp/ex --work /tmp/ex-work --draft examples/input/draft.json
```

## What the ledger checks

- `config.json` 摊平成 `optimizer.lr = 0.001`、`training.batch_size = 64` 等 13 条；
- `train.log` 的 `lr=0.001`、`count=4` 等进入台账；
- 正文每个数字都能溯源（0.001 / 64 / 40 / 42 / 500 / 4 / 32GB / 2.1.0 / 2.0 / 80% / 10%）；
- 六类要素齐全；
- 八项复现清单齐全（含运行命令 `python train.py ...`）；
- 基线 `BERT-base` + 同预算、数据集 `GLUE` + `version 2.0` + `80/10/10` 划分。

## Illustrative output (EXAMPLE -- not an official case result)

`methods.md` 文末的参数台账（节选）：

| name | value | unit | source |
|---|---|---|---|
| optimizer.lr | 0.001 |  | config.json:3 |
| optimizer.weight_decay | 0.01 |  | config.json:3 |
| training.batch_size | 64 |  | config.json:4 |
| training.epochs | 40 |  | config.json:4 |
| training.seed | 42 |  | config.json:4 |
| data.version | 2.0 |  | config.json:5 |

`result.json` 的关键指标：

```json
{"status": "success",
 "metrics": {"params": 20, "numbers_sourced": 16, "n_numbers": 16,
             "coverage": 1.0, "repro_items": 8}}
```

> 说明：以上是**示例输出**，用来说明接口和校验形态；它不是平台正式案例的结果。
