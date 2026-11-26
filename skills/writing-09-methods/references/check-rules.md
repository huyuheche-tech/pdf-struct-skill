# 方法章节检查规则与返修边界

所有检查都是确定性的，只看 draft 与参数台账/材料，不评价文笔。

## number_unsourced

- 触发：正文某个数字（去掉 `[TODO: ...]` 与标题/列表编号后）不在参数台账或材料数字集合里。
- 通过：每个数字都能在台账 `value` 或任一材料原文中找到。
- 误报边界：`V100` 里的 `100` 因紧邻字母不会被当成数字；`2.1.0` 取 `2.1`；`32 GB` 与 `32GB` 去空格后等价。
- 返修：改回材料值，或把含该数字的材料补进输入；不要改检查器。

## category_missing

- 触发：六类要素（steps / setup / params / dataset / baselines / repro）任一没有任何关键词命中。
- 通过：每类至少 1 个关键词（见 `methods_ledger.CATEGORY_KW`）。
- 误报边界：只写标题不算；关键词命中是必要条件，不是充分条件，仍需人工确认内容真实。
- 返修：补写该类内容，不要只塞关键词。

## repro_gap

- 触发（gap）：八项复现清单缺项，且正文未声称 reproducible。
- 触发（error）：正文出现 `reproducib* / 可复现 / 可重现`，同时清单缺项。
- 八项：seed、数据版本、split、batch size、学习率、epochs、硬件/框架版本、运行命令。
- 误报边界：`env` 一项要求同时出现硬件、框架名、框架版本号；只有 "GPU" 不算。
- 返修：补齐缺项；补不了就不要声称可复现。gap 要在 `uncertainty.gaps` 如实列出。

## baseline_underspecified

- 触发：没有基线/对照语句；或基线语句里没有名称，或没有同预算条件。
- 通过：基线窗口内出现（a）具体名称（`BERT-base`、`GLUE` 这类大写/连字符 token），
  且（b）同预算表述（`same training budget`、`相同训练预算`、`同等算力` 等）。
- 误报边界：只写 "we compare with baselines" 不算；名称可以是引用 key 指向的模型名。
- 返修：补基线名称与预算条件（epochs / steps / tokens 任一）。

## dataset_underspecified

- 触发：没有数据集语句；或数据集窗口缺名称 / 版本或规模 / 划分之一。
- 通过：窗口内同时有名称、`version`/`v1.0`/`132k examples`/`版本`/`规模` 之一、以及
  `split`/`train/val/test`/`划分` 之一。
- 误报边界：框架版本（`PyTorch 2.1.0`）不会满足数据集版本，因为检查限定在含数据集关键词的窗口。
- 返修：补 `名称 + 版本/规模 + 划分`，不要用"公开数据集"含糊带过。
