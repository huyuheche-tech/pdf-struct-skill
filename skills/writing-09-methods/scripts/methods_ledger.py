# -*- coding: utf-8 -*-
"""methods_ledger -- deterministic parameter ledger for a methods section.

The model writes the prose; this module guarantees the parts a language model
must not be trusted with:

  * a parameter ledger flattened from config.json / config.yaml / train.log,
    each row carrying name / value / unit / source(file:line);
  * number-to-source checking (every number in the body must appear in the
    ledger or in the raw materials, otherwise `number_unsourced`);
  * six-element coverage (steps / setup / parameters / dataset / baselines /
    reproducibility & limitations);
  * an eight-item reproducibility checklist, reported as gaps unless the body
    claims reproducibility, in which case they become hard errors;
  * baseline and dataset specification checks.

It never writes the section.  Without a draft it emits params.json and a
hand-off instruction and marks the result "partial".
"""
from __future__ import print_function

import json
import os
import re

import skillkit as sk

TODO_RE = re.compile(r"\[TODO:[^\]]*\]", re.I)
HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
LIST_RE = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+")
TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$")

CATEGORY_KW = {
    "steps": re.compile(
        r"(?:\bstep|\bprocedure|\bpipeline|\btraining loop|\bfirst\b|\bthen\b|"
        r"\bfinally\b|\balgorithm\b|步骤|流程|首先|然后|最后|训练过程)", re.I),
    "setup": re.compile(
        r"(?:\bsetup\b|\benvironment\b|\bhardware\b|\bGPU|\bCPU\b|\bframework\b|"
        r"\bPyTorch\b|\bTensorFlow\b|\bJAX\b|实验设置|环境|硬件|框架|显卡)", re.I),
    "params": re.compile(
        r"(?:\blearning rate\b|\bbatch[\s_-]?size\b|\bepochs?\b|\bseed\b|"
        r"\bweight decay\b|\bwarmup\b|\bhyperparameter|\blr\b|学习率|批大小|"
        r"批量|迭代|参数|随机种子|权重衰减)", re.I),
    "dataset": re.compile(
        r"(?:\bdataset|\bcorpus|\bbenchmark|\bdata set|\btraining set|数据集|语料|训练集)", re.I),
    "baselines": re.compile(
        r"(?:\bbaseline|\bcompare|\bcomparison\b|\bcontrol\b|基线|对照|对比)", re.I),
    "repro": re.compile(
        r"(?:\breproduc|\breplicate|\blimitation|\bcode is available\b|"
        r"\bopen[- ]source\b|复现|重现|局限|限制|开源)", re.I),
}

REPRO_ITEMS = [
    ("seed", re.compile(r"\bseed\b|随机种子|种子", re.I)),
    ("data_version", re.compile(r"\bversion\b|\bv\d+(?:\.\d+)*\b|版本", re.I)),
    ("split", re.compile(
        r"\bsplit\b|\btrain(?:ing)?\b[\s,/、]*(?:val|validation|dev|test)|"
        r"\b训练(?:集)?\b[\s,/、]*(?:验证|测试)|划分", re.I)),
    ("batch_size", re.compile(r"\bbatch[\s_-]?size\b|批大小|批量大小", re.I)),
    ("learning_rate", re.compile(r"\blearning[\s_-]?rate\b|\blr\b|学习率", re.I)),
    ("epochs", re.compile(r"\bepochs?\b|轮次|迭代轮|轮", re.I)),
    ("command", re.compile(
        r"\bpython\s+[^\s]+\.py\b|\btorchrun\b|\bdeepspeed\b|\bbash\s+[^\s]+|"
        r"运行命令|命令行|\$\s*\w+", re.I)),
]
HARDWARE_RE = re.compile(r"\bGPU|\bCPU|\bTPU|NVIDIA|A100|V100|H100|显卡|硬件", re.I)
FRAMEWORK_RE = re.compile(r"\bPyTorch\b|\bTensorFlow\b|\bJAX\b|\bMXNet\b|\bCUDA\b|框架", re.I)
FRAMEWORK_VER_RE = re.compile(
    r"(?:pytorch|tensorflow|jax|cuda|mxnet)\s*v?\d+(?:\.\d+)+|框架版本", re.I)
CLAIM_REPRO_RE = re.compile(r"\breproducib|可复现|可重现|fully reproducible", re.I)

BASELINE_KW = re.compile(r"\bbaseline|\bcompare|\bcomparison\b|\bcontrol\b|基线|对照|对比", re.I)
DATASET_KW = re.compile(r"\bdataset|\bcorpus|\bbenchmark|\bdata set|\btraining set|数据集|语料|训练集", re.I)
NAME_RE = re.compile(r"[A-Z][A-Za-z0-9]+(?:-[A-Za-z0-9]+)+")
ACRONYM_RE = re.compile(r"\b[A-Z]{3,}\b")
STOP = frozenset(("THE", "WE", "OUR", "UNDER", "SAME", "ALL", "FOR", "IN", "ON",
                  "WITH", "AND", "BASELINE", "BASELINES", "COMPARED", "COMPARE",
                  "THIS", "THAT", "THESE", "THOSE", "TRAINING", "TEST",
                  "VALIDATION", "TRAIN", "BATCH", "EPOCHS", "EPOCH"))
BUDGET_RE = re.compile(
    r"\b(?:same|identical|equal|comparable|matched)\b.{0,48}"
    r"\b(?:budget|compute|epochs?|steps|tokens|training)\b|"
    r"\b(?:budget|compute|epochs?|steps|tokens)\b.{0,48}"
    r"\b(?:same|identical|equal|matched)\b|"
    r"同等.{0,16}(?:预算|轮数|步数|算力)|"
    r"相同.{0,16}(?:预算|轮数|步数|算力)|"
    r"(?:预算|轮数|步数).{0,16}(?:相同|同等)", re.I)
SCALE_RE = re.compile(
    r"\bversion\b|\bv\d+(?:\.\d+)*\b|"
    r"\b\d+(?:\.\d+)?\s*(?:k|K|M|examples|samples|images|sentences)\b|"
    r"版本|规模|万|条样本|样本|条数据", re.I)
SPLIT_RE = re.compile(
    r"\bsplit\b|\btrain(?:ing)?\b[\s,/、]*(?:val|validation|dev|test)|"
    r"\b训练(?:集)?\b[\s,/、]*(?:验证|测试)|划分|80\s*[/%]\s*10", re.I)


# --------------------------------------------------------------------------
# flatten config sources
# --------------------------------------------------------------------------
def _unquote(v):
    v = (v or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def _line_of(text, needle):
    for i, line in enumerate((text or "").splitlines(), 1):
        if needle and needle in line:
            return i
    return 1


def flatten_json(obj, prefix=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(flatten_json(v, "%s.%s" % (prefix, k) if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(flatten_json(v, "%s[%d]" % (prefix, i)))
    else:
        out.append((prefix, "" if obj is None else str(obj)))
    return out


def flatten_yaml(text):
    out, stack = [], []
    for i, raw in enumerate((text or "").splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        if ":" not in body:
            continue
        key, val = body.split(":", 1)
        key, val = _unquote(key.strip()), val.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        prefix = ".".join(k for _ind, k in stack)
        full = "%s.%s" % (prefix, key) if prefix else key
        if val == "":
            stack.append((indent, key))
        else:
            out.append((full, _unquote(val), i))
    return out


def parse_log(text):
    out = []
    for i, line in enumerate((text or "").splitlines(), 1):
        for m in re.finditer(r"--([A-Za-z][\w\-]*)\s+([^\s,;]+)", line):
            out.append((m.group(1), _unquote(m.group(2)), i))
        for m in re.finditer(r"\b([A-Za-z_][\w\-.]*)\s*=\s*([^\s,;]+)", line):
            out.append((m.group(1), _unquote(m.group(2)), i))
        if "=" not in line:
            for m in re.finditer(r"\b([A-Za-z_][\w\-.]*)\s*:\s*([^\s,;]+)", line):
                out.append((m.group(1), _unquote(m.group(2)), i))
    return out


UNIT_SUFFIX = {"%": "%", "gb": "GB", "mb": "MB", "tb": "TB", "kb": "KB",
               "ms": "ms", "s": "s", "min": "min", "h": "h",
               "bp": "bp", "kda": "kDa", "da": "Da"}
DIMENSIONLESS = ("lr", "learning_rate", "learning rate", "weight_decay",
                 "weight decay", "dropout", "batch", "batch_size", "batch size",
                 "epoch", "epochs", "seed", "step", "steps", "warmup",
                 "length", "layer", "layers", "head", "heads")


def infer_unit(name, value):
    v = str(value or "").strip()
    m = re.search(r"(%|[A-Za-z]+)\s*$", v)
    if m:
        suf = m.group(1)
        if suf.lower() in UNIT_SUFFIX:
            return UNIT_SUFFIX[suf.lower()]
    low = (name or "").lower()
    if any(k in low for k in DIMENSIONLESS):
        return ""
    return ""


def build_params(materials):
    rows = []
    for m in materials:
        kind = m.get("kind")
        name = m.get("name") or ""
        text = m.get("text") or ""
        pairs = []
        if kind == "json":
            try:
                obj = json.loads(text)
            except Exception:
                continue
            if not isinstance(obj, (dict, list)):
                continue
            for flat_name, val in flatten_json(obj):
                if not flat_name:
                    continue
                leaf = re.split(r"[.\[]", flat_name)[-1].rstrip("]")
                pairs.append((flat_name, val, _line_of(text, leaf or flat_name)))
        elif kind == "yaml":
            pairs = flatten_yaml(text)
        elif kind in ("text", "csv") and name.lower().endswith(".log"):
            pairs = parse_log(text)
        for nm, val, line in pairs:
            if not nm or val is None:
                continue
            val = str(val).strip()
            if not val or val.lower() in ("none", "null", "true", "false"):
                continue
            rows.append({"name": nm, "value": val, "unit": infer_unit(nm, val),
                         "source": "%s:%d" % (name or "material", line)})
    # de-duplicate identical name+value, keeping the first source
    seen, out = set(), []
    for r in rows:
        k = (r["name"], r["value"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


# --------------------------------------------------------------------------
# draft
# --------------------------------------------------------------------------
def draft_body(draft):
    if isinstance(draft, str):
        return draft, []
    if not isinstance(draft, dict):
        return "", []
    for k in ("methods", "text", "body", "content", "raw"):
        v = draft.get(k)
        if isinstance(v, str) and v.strip():
            params = draft.get("params") if isinstance(draft.get("params"), list) else []
            return v, params
    return "", []


def scan_text(body):
    text = TODO_RE.sub(" ", body or "")
    kept = []
    for line in text.splitlines():
        if HEADING_RE.match(line):
            continue
        if TABLE_SEP_RE.match(line):
            continue
        line = LIST_RE.sub("", line)
        kept.append(line)
    return "\n".join(kept)


def tokens(text):
    return [re.sub(r"\s+", "", n["raw"]).lower() for n in sk.numbers(text)]


def sentences(body):
    out = []
    for line in (body or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = sk.split_sentences(line) or [line]
        out.extend(parts)
    return out


def window(sents, rx, size=3):
    blocks = []
    for i, s in enumerate(sents):
        if rx.search(s):
            blocks.append(" ".join(sents[i:i + size]))
    return blocks


def has_name(block):
    for m in NAME_RE.finditer(block):
        if m.group(0).split("-")[0].upper() not in STOP:
            return True
    for m in ACRONYM_RE.finditer(block):
        if m.group(0) not in STOP:
            return True
    return False


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------
def validate(body, params, allowed_tokens):
    errors, warnings, gaps = [], [], []
    clean = scan_text(body)

    # 1. every number traceable
    n_numbers, sourced = 0, 0
    for tok in tokens(clean):
        n_numbers += 1
        if tok in allowed_tokens:
            sourced += 1
        else:
            errors.append({"code": "number_unsourced",
                           "detail": "number %r is not in the parameter ledger or materials" % tok})
    # 1b. if a parameter name immediately precedes a number, the number must be
    # exactly that parameter's value -- "sourced somewhere" is not enough.
    named = sorted(((sk.norm_key(r.get("name") or ""), r) for r in params),
                   key=lambda x: -len(x[0]))
    for m in sk.numbers(clean):
        start = m["span"][0]
        ctx = sk.norm_key(clean[max(0, start - 50):start]).rstrip()
        tok = re.sub(r"\s+", "", m["raw"]).lower()
        hit = None
        for nm, row in named:
            if nm and ctx.endswith(nm):
                hit = row
                break
        if hit is not None:
            allowed_vals = set(tokens(str(hit.get("value"))))
            if tok not in allowed_vals:
                errors.append({"code": "number_mismatch",
                               "detail": "%s is %r in the ledger but the text says %r"
                                         % (hit.get("name"), hit.get("value"), m["raw"])})
    for m in TODO_RE.finditer(body or ""):
        gaps.append({"code": "todo_placeholder", "detail": m.group(0)})

    # 2. six-element coverage
    covered = 0
    for cat, rx in CATEGORY_KW.items():
        if rx.search(body or ""):
            covered += 1
        else:
            errors.append({"code": "category_missing", "category": cat,
                           "detail": "no keyword for the %r element" % cat})

    # 3. reproducibility checklist
    present = {}
    for item, rx in REPRO_ITEMS:
        present[item] = bool(rx.search(body or ""))
    present["env"] = bool(HARDWARE_RE.search(body or "") and FRAMEWORK_RE.search(body or "")
                          and FRAMEWORK_VER_RE.search(body or ""))
    missing = [k for k, ok in present.items() if not ok]
    for item in missing:
        gaps.append({"code": "repro_gap", "item": item,
                     "detail": "reproducibility checklist item %r is missing" % item})
    if missing and CLAIM_REPRO_RE.search(body or ""):
        for item in missing:
            errors.append({"code": "repro_gap", "item": item,
                           "detail": "body claims reproducibility but %r is missing" % item})
    repro_items = sum(1 for ok in present.values() if ok)

    # 4. baseline specification
    sents = sentences(body)
    base_blocks = window(sents, BASELINE_KW)
    if not base_blocks:
        errors.append({"code": "baseline_underspecified",
                       "detail": "no baseline / comparison statement found"})
    else:
        joined = " ".join(base_blocks)
        if not has_name(joined) or not BUDGET_RE.search(joined):
            errors.append({"code": "baseline_underspecified",
                           "detail": "baseline needs a name and a matched-budget condition"})

    # 5. dataset specification
    data_blocks = window(sents, DATASET_KW)
    if not data_blocks:
        errors.append({"code": "dataset_underspecified",
                       "detail": "no dataset statement found"})
    else:
        joined = " ".join(data_blocks)
        miss = []
        if not has_name(joined):
            miss.append("name")
        if not SCALE_RE.search(joined):
            miss.append("version/scale")
        if not SPLIT_RE.search(joined):
            miss.append("split")
        if miss:
            errors.append({"code": "dataset_underspecified",
                           "detail": "dataset statement missing: " + ", ".join(miss)})

    metrics = {"params": len(params), "numbers_sourced": sourced,
               "n_numbers": n_numbers,
               "coverage": round(covered / float(len(CATEGORY_KW)), 3),
               "repro_items": repro_items}
    return errors, warnings, gaps, metrics, present


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def render(body, params, title):
    lines = ["# %s" % (title or "Methods"), ""]
    lines.append((body or "_(not written)_").strip())
    lines.append("")
    lines.append("## Parameter ledger")
    lines.append("")
    lines.append("| name | value | unit | source |")
    lines.append("|---|---|---|---|")
    for r in params:
        lines.append("| %s | %s | %s | %s |" % (r["name"], r["value"],
                                                 r["unit"] or "", r["source"]))
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------
def run(case, materials, out_dir, draft_path=None):
    if not materials:
        main = {"case_id": sk.case_id_of(case, []), "methods": "", "tables": [],
                "gaps": [],
                "checks": {"errors": [{"code": "no_material"}], "warnings": []},
                "metrics": {"params": 0, "numbers_sourced": 0, "coverage": 0,
                            "repro_items": 0}}
        return {"status": "failed", "main": main, "errors": [{"code": "no_material"}],
                "warnings": [], "has_draft": False, "sources": []}

    params = build_params(materials)
    sk.jdump(os.path.join(out_dir, "params.json"),
             {"n_params": len(params), "params": params})

    allowed = set()
    for m in materials:
        allowed.update(tokens(m.get("text") or ""))
    for r in params:
        allowed.update(tokens(r["value"]))

    draft = sk.load_draft(draft_path)
    body, draft_params = draft_body(draft)
    has_draft = bool(body.strip())
    if draft_params:
        for r in draft_params:
            if not isinstance(r, dict):
                continue
            nm, val = r.get("name"), r.get("value")
            if not nm or val is None:
                continue
            row = {"name": str(nm), "value": str(val),
                   "unit": r.get("unit") or infer_unit(nm, val),
                   "source": r.get("source") or "draft"}
            params.append(row)
            allowed.update(tokens(row["value"]))

    if has_draft:
        errors, warnings, gaps, metrics, present = validate(body, params, allowed)
    else:
        errors = [{"code": "category_missing", "category": c,
                   "detail": "no methods body supplied"} for c in CATEGORY_KW]
        warnings, gaps = [], []
        metrics = {"params": len(params), "numbers_sourced": 0, "n_numbers": 0,
                   "coverage": 0.0, "repro_items": 0}
        present = {}

    sk.jdump(os.path.join(out_dir, "gaps.json"),
             {"n_gaps": len(gaps), "gaps": gaps,
              "repro_checklist": present})

    status = "partial" if (not has_draft or errors) else "success"
    title = (case or {}).get("title") if isinstance(case, dict) else None
    md = render(body, params, title)
    with open(os.path.join(out_dir, "methods.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)

    checks = {"errors": errors, "warnings": warnings, "gaps": gaps,
              "summary": {"n_errors": len(errors), "n_warnings": len(warnings),
                          "n_gaps": len(gaps), "metrics": metrics}}
    sk.jdump(os.path.join(out_dir, "checks.json"), checks)

    main = {
        "case_id": sk.case_id_of(case, [m["path"] for m in materials]),
        "status": status,
        "methods": body,
        "tables": params,
        "checks": checks,
        "metrics": metrics,
        "files": {"methods": "methods.md", "params": "params.json",
                  "gaps": "gaps.json", "checks": "checks.json"},
    }
    return {"status": status, "main": main, "errors": errors, "warnings": warnings,
            "gaps": gaps, "has_draft": has_draft,
            "sources": [m["path"] for m in materials]}
