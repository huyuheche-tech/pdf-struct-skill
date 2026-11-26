# Example: one small manuscript, three warnings, no errors

> 本目录是**最小调用示例**，其中的输出标注为 EXAMPLE，**不是平台正式案例的结果**。

## 输入

```
examples/
  case.json     # case_id=example-latex, compile=false
  main.tex      # 4 个宏包里有 1 个重复；1 张没有 caption 的表；1 条引用
  refs.bib      # 2 条，正文只引了 1 条
  draft.tex     # 模型复核后的主文件（此处与 main.tex 相同）
```

## 运行

```bash
python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out /tmp/ex --work /tmp/ex-work --fix

python scripts/run_case.py --case examples/case.json --input-dir examples \
    --out /tmp/ex --work /tmp/ex-work --draft examples/draft.tex --no-compile
```

## 检查了什么

- `\usepackage{booktabs}` 出现两次 → `package_duplicate`（warning，第 4 行）；
- 表格没有 `\caption` → `caption_missing`（warning）；
- `refs.bib` 里 `karpukhin2020dpr` 没被引用 → `bib_unused`（warning）；
- 表格是 `{lc}`、两行各 2 列 → 不报；
- 本机没有 TeX → `compiled=false`、`compiler_missing=true`，报告写"未编译"。

## 示例输出（EXAMPLE，不是正式评测结果）

```text
$ python scripts/run_case.py --case examples/case.json --input-dir examples \
      --out /tmp/ex --work /tmp/ex-work --draft examples/draft.tex --no-compile
case_id=example-latex status=success errors=0 warnings=3 compiled=False fixes=0
```

`report.md` 片段：

```markdown
- errors: 0, warnings: 3
- compiled: False (compiler missing)

## 警告（需人工确认）

- `package_duplicate` **main.tex:4** — 宏包 'booktabs' 重复加载（首次第 2 行）
  ```latex
  \usepackage{booktabs}
  ```
- `caption_missing` **main.tex:11** — table 环境没有 \caption
- `bib_unused` **refs.bib:9** — 该条目在正文中没有被引用
```

`result.json` 的 `main_result.metrics`：

```json
{"errors": 0, "warnings": 3, "compiled": false,
 "cite_keys": 1, "labels": 1, "lines": 22}
```

status 为 `success` 是因为**有 draft 且 0 个 error**；三条 warning 仍需人工判断，
它们会出现在 `uncertainty.human_review` 里。`compiled=false` 是本机没有 TeX 的
如实记录，**不是**"编译通过"。
