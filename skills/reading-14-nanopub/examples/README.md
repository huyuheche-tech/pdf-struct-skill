# 示例：一段摘要 → 三条断言（EXAMPLE）

> 本目录是**最小调用示例**，输出仅用于说明接口形态，**不是**平台正式案例结果。

## 运行

```bash
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out-example --work ./work-example --outline

python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out-example --work ./work-example --draft examples/draft.json
```

## 产物（示意，EXAMPLE）

`out-example/nanopub.json`：

```json
{"assertion": {"assertions": [
   {"id": "a1", "uri": "urn:nanopub:deda5ec10871e8ea",
    "text": "Temperature scaling lowers expected calibration error from 11.2% to 4.8% on CIFAR-100.",
    "subject": "temperature scaling", "predicate": "has_property",
    "object": "expected calibration error 4.8%", "conditions": "", "confidence": "high"}]},
 "provenance": [{"assertion_id": "a1", "source_id": "example-cifar100-temperature",
                 "doi": "10.0000/example.nanopub.01", "paragraph_id": "s02.p01",
                 "quote": "On CIFAR-100, temperature scaling lowers expected calibration error from 11.2% to 4.8%.",
                 "char_span": [194, 281]}],
 "pubinfo": {"creator": "nanopub-assertion-builder", "created": "2026-01-15T00:00:00Z",
             "license": "CC-BY-4.0", "template": "nano-pub/1"}}
```

`out-example/assertions.md` 摘要：

| id | 断言 | 证据 | 位置 | 置信度 |
|---|---|---|---|---|
| a1 | Temperature scaling lowers ECE from 11.2% to 4.8% on CIFAR-100. | On CIFAR-100, temperature scaling lowers ECE from 11.2% to 4.8%. | s02.p01 | high |
| a2 | Under 20% label noise, the method keeps ECE at 6.1%. | Under label noise (20%), the method still lowers the error to 6.1%. | s02.p01 | medium |
| a3 | Temperature scaling adds no inference cost. | The method adds no inference cost. | s02.p01 | high |

> 以上为 **EXAMPLE** 输出（本地示例的真实运行结果），说明三段结构与校验形态；
> 真实案例请按 `tests/cases/` 的输入自测。
