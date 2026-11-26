# 数据契约

## 1. 输入材料（自动识别，不靠文件名）

| 形态 | 识别依据 | 解析成 |
|---|---|---|
| BibTeX | 扩展名 `.bib`；`@article{key, field = {value}}`，支持嵌套花括号与 `and` 作者 | 每条 `key/type/fields` |
| RIS | 扩展名 `.ris`；`TY  - JOUR` … `ER  -` | 同上 |
| 编号文本 | 首个非空行匹配 `^\s*\[\d+\]\s+\S` | 同上（带 `number`） |
| 正文 | 剩下的 `.md` / `.txt` / `.pdf` 中**最长**的一段 | 引用解析对象 |

正文引用四种形态：

| 形态 | 例 | 解析结果 |
|---|---|---|
| 单个编号 | `[1]` | ids `["1"]` |
| 多个编号 | `[2,4]` | ids `["2","4"]` |
| 区间 | `[3-5]` | ids `["3","4","5"]`（跨度 >30 视为排版噪声，不展开） |
| LaTeX | `\cite{a,b}` | ids `["a","b"]`（按 key 匹配，**不改写**） |
| 作者-年份 | `(Smith et al., 2020)` / `(Chen, 2019; Liu, 2021)` | 按"第一作者姓氏 + 年份"匹配 |

## 2. draft.json（编辑决策）

```json
{"merges": [["chen2019conf", "chen2019j"]],
 "declared_complete": ["chen2019j", "liu2021"],
 "notes": "free text, not validated"}
```

| 字段 | 约束 |
|---|---|
| `merges` | 每个元素是 `["keyA","keyB"]`；引擎复核，不够格 → `unsafe_merge` 并拒绝 |
| `declared_complete` | 声称字段齐全的 key；缺字段 → `field_missing`（severity=error） |
| `notes` | 自由文本，原样留在 `references.json` 之外（不进 result），仅供人看 |

两个键都可为空列表——空列表本身是一次明确决策，因此**有 draft 文件**（哪怕是 `{}`）就算决策已做。

## 3. references.json

```json
{
 "entries": [
  {"id": "r02", "key": "chen2019j", "type": "J",
   "number_old": 2, "number_new": 2,
   "authors": ["Wei Chen", "Lin Zhao"],
   "title": "Attention improves sample efficiency in low-resource settings",
   "year": "2019", "source": "Journal of Machine Learning Research",
   "volume": "20", "issue": "4", "pages": "1-25", "doi": "10.1000/acl.2019.210",
   "cited": true, "cite_count": 2,
   "completeness": {"author": true, "title": true, "year": true, "source": true, "doi": true},
   "complete": true, "todo": [],
   "merged_from": ["chen2019conf"],
   "gbt7714": "Chen W, Zhao L. Attention ...[J]. JMLR, 2019, 20(4): 1-25. DOI: ...",
   "apa": "Chen, W., & Zhao, L. (2019). ..."}
 ],
 "renumber_map": [{"old": 1, "key": "chen2019conf", "new": 2,
                   "merged_into": "chen2019j", "cited": true}],
 "merges": [{"keys": ["chen2019conf","chen2019j"], "kept": "chen2019j",
             "dropped": "chen2019conf", "basis": "doi", "detail": "identical DOI ..."}],
 "issues": {"errors": [], "warnings": []},
 "style": "gbt7714",
 "format": "bib"
}
```

- `entries` 只含**合并后**的条目（`merged_from` 列出被并掉的 key）；
- `renumber_map` 覆盖**每一条原始条目**，`new` 是合并后的新编号，`merged_into` 指明去向；
- `number_old`：编号表用自己的 `[n]`；`.bib` / `.ris` 用文件里的位置（1 起）。

## 4. checks.json

```json
{
 "errors": [{"code": "missing_entry", "detail": "cited but not in the bibliography: '[2,4]'"}],
 "warnings": [{"code": "uncited_entry", "detail": "zhou2018 is in the bibliography but never cited"},
              {"code": "field_missing", "key": "zhou2018", "field": "doi", "severity": "warning"}],
 "citations": [{"raw": "[2,4]", "style": "numeric", "keys": ["liu2021", null]}],
 "summary": {"n_errors": 1, "n_warnings": 2, "n_citations": 3, "style": "gbt7714"}
}
```

## 5. result.json（平台契约）

| 字段 | 说明 |
|---|---|
| `main_result.references[]` | 同上 `entries` |
| `main_result.renumber_map[]` | 同上 |
| `main_result.checks` | 同上 `checks.json` |
| `main_result.metrics` | `entries`（合并后）/ `parsed_entries`（合并前）/ `cited` / `uncited` / `missing` / `duplicates` / `field_completeness` |
| `main_result.bibliography` | `bibliography.md` 全文 |
| `main_result.manuscript_renumbered` | 改写后正文；`--check-only` 下为 `""` |
| `main_result.merges` | 合并记录（含 `basis`） |
| `main_result.files` | 产物文件名 |
| `output_contract` | 按契约回填；无法识别写 `null` 进 `contract_unresolved` |

## 6. status 判定

| 情形 | status |
|---|---|
| 没有可读正文 | `failed`（`no_manuscript`） |
| 没有文献表 | `failed`（`no_library`） |
| 没有 draft（`--check-only` 或平台没给） | `partial` + `uncertainty.next_step` |
| 有 draft 且有 error | `partial` |
| 有 draft 且 0 error | `success` |

`--check-only` 永远不是 `success`：它没有做"改写正文"这一步，把它写成成功就是虚报。
