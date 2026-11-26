# 语料来源与校验（corpus/ 未随包分发）

五篇都是公开 arXiv 预印本，**没有打包进 bundle**（体积 + 再分发许可）。复现时按下面任一方式取回，
再用 `sha256` 校验；`doc.json.source.sha256` 记录的就是这个值，两边对上即证明"你跑的是同一份文件"。

| 文件 | arXiv | 下载地址 | 字节 | sha256 |
|---|---|---|---|---|
| `resnet.pdf` | 1512.03385 *Deep Residual Learning for Image Recognition* | https://arxiv.org/pdf/1512.03385 | 819,383 | `1e0651b6810ecba34a3dbc5b5b0209226f889004607c1f203540a48d64e5a93a` |
| `transformer.pdf` | 1706.03762 *Attention Is All You Need* | https://arxiv.org/pdf/1706.03762 | 2,215,244 | `bdfaa68d8984f0dc02beaca527b76f207d99b666d31d1da728ee0728182df697` |
| `bert.pdf` | 1810.04805 *BERT: Pre-training of Deep Bidirectional Transformers* | https://arxiv.org/pdf/1810.04805 | 775,166 | `5692a5514787a8c6727b4ff3b726a3385798bc68e12138d1d4af83947e2acf6e` |
| `gpt3.pdf` | 2005.14165 *Language Models are Few-Shot Learners* | https://arxiv.org/pdf/2005.14165 | 6,768,044 | `97fd272f1fdfc18677462d0292f5fbf26ca86b4d1b485c2dba03269b643a0e83` |
| `vit.pdf` | 2010.11929 *An Image is Worth 16x16 Words*（留出样本） | https://arxiv.org/pdf/2010.11929 | 3,587,206 | `f031259d8c15905506f3cf3d376b695b3110cb6f724792d5396776dcae610b16` |

一键回填（需要网络）：

```bash
mkdir -p corpus
for id in 1512.03385 1706.03762 1810.04805 2005.14165 2010.11929; do
  curl -L -o "corpus/$id.pdf" "https://arxiv.org/pdf/$id"
done
python - <<'PY'
import glob, hashlib
for p in sorted(glob.glob("corpus/*.pdf")):
    print(hashlib.sha256(open(p, "rb").read()).hexdigest(), p)
PY
```

> 注意：arXiv 会更新版本，`1512.03385v1` 与 `v2` 的字节可能不同。上表的 sha256 对应本 bundle
> `results/*/report.json` 里记录的那一版；若你的校验值不同，解析结果仍可用，但页数/块数可能与
> `results/run.log` 相差 ±1，属正常。
