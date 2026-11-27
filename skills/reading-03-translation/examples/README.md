# Example: one paragraph, one locked term, one number

## Input (`examples/case.json` + `examples/material.md` + `examples/glossary.csv`)

```bash
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out /tmp/ex --work /tmp/ex-work --plan-only
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out /tmp/ex --work /tmp/ex-work --draft examples/draft.json
```

## What the guard checks

- `p001` exists and is translated;
- `18.4%` and `p<0.001` appear byte-for-byte in the target;
- `[3]` and `[7]` survive;
- the locked term `attention mechanism -> 注意力机制` is used;
- `may` is not turned into a certainty.

## Illustrative output (EXAMPLE -- not an official case result)

| 段号 | 位置 | 原文 | 译文 | 校验 |
|---|---|---|---|---|
| p001 | abstract | We report a 12-week trial of 240 participants. The attention mechanism reduced errors by 18.4% (p<0.001) [3]. This may explain the gain [7]. | 我们报告了一项为期 12 周、240 名受试者的试验。注意力机制使错误率下降 18.4%（p<0.001）[3]。这可能解释了该增益 [7]。 | OK |

`checks.json` 中该段的 `glossary_matrix` 行为 `attention mechanism / 注意力机制 / abstract 1/1 / consistent true`。

> 说明：以上是**示例输出**，用来说明接口和校验形态；它不是平台正式案例的结果。
