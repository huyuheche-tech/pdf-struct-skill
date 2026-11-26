# 示例：两节小论文 → 论文卡片（EXAMPLE）

> 本目录是**最小调用示例**，输出仅用于说明接口形态，**不是**平台正式案例结果。

## 运行

```bash
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out-example --work ./work-example --outline

python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out ./out-example --work ./work-example --draft examples/draft.json
```

## 产物（示意，EXAMPLE）

`out-example/result.json` 中：

```json
{"status": "success",
 "main_result": {"metrics": {"sections": 2, "covered": 2,
                             "fields_complete": "5/5",
                             "anchors_resolved": "6/6", "duplicates": 0}}}
```

`out-example/notes.md` 摘要：

| 字段 | 内容 | 锚点 |
|---|---|---|
| 研究问题 | 冻结句向量上的线性探针能否恢复情感标签？ | s01.p01 |
| 数据 | 三个评论数据集。 | s01.p01 |
| 方法 | 线性探针，训练 20 轮、批大小 128。 | s01.p01 |
| 发现 1 | 准确率 91.2%，比逻辑回归基线高 3.1 点。 | s01.p01 |
| 发现 2 | 仅 10% 训练标注时增益仍然存在。 | s02.p01 |
| 局限 1 | 只评估英语评论。 | s02.p01 |

`checks.json`：`errors: []`，`summary.n_sections = 2`。

> 以上为 **EXAMPLE** 输出，用来说明字段与校验形态；真实案例请按 `tests/cases/` 的输入自测。
