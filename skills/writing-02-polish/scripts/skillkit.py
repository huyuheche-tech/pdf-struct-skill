# -*- coding: utf-8 -*-
"""skillkit -- shared, stdlib-only helpers for the weekly-skill submissions.

Every skill in this folder ships a copy of this file so that it is
self-contained: the evaluator installs one skill directory under
/skills/weekly-skill and nothing else is importable.

Design rules
------------
* No network, no third-party imports at module import time.  pymupdf is used
  only if it happens to be installed (the pinned image has a PDF text tool).
* Everything that ends up in result.json is JSON-serialisable and UTF-8.
* Console output is ASCII only (the authoring machine has a GBK console); all
  human-readable prose goes into files.
* Never invent content.  Missing input is reported as a warning and the
  result is marked "partial".
"""
from __future__ import print_function

import difflib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import zlib

SCHEMA = "weekly-skill/result/1"
TEXT_EXT = (".txt", ".md", ".markdown", ".json", ".jsonl", ".csv", ".tsv",
            ".yaml", ".yml", ".tex", ".bib", ".ris", ".html", ".htm", ".xml")
PDF_EXT = (".pdf",)


# --------------------------------------------------------------------------
# IO
# --------------------------------------------------------------------------
def jload(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def jdump(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    """Read a text file, tolerating BOM and a few legacy encodings."""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


def norm_ws(s):
    s = (s or "").replace("\u00a0", " ").replace("\u3000", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def one_line(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


# --------------------------------------------------------------------------
# PDF text (best effort, three tiers)
# --------------------------------------------------------------------------
def _pdf_pages_pymupdf(path):
    import fitz  # noqa: F401  (optional)
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        blocks = []
        for b in page.get_text("blocks") or []:
            # (x0, y0, x1, y1, text, block_no, block_type)
            if len(b) >= 7 and b[6] != 0:
                continue
            txt = norm_ws(b[4])
            if not txt:
                continue
            blocks.append({"bbox": [round(float(b[0]), 1), round(float(b[1]), 1),
                                    round(float(b[2]), 1), round(float(b[3]), 1)],
                           "text": txt})
        pages.append({"page": i + 1,
                      "text": norm_ws(page.get_text("text") or ""),
                      "blocks": blocks})
    meta = {"extractor": "pymupdf", "pages": len(pages),
            "encrypted": bool(getattr(doc, "is_encrypted", False))}
    doc.close()
    return pages, meta


def _pdf_pages_pdftotext(path):
    exe = None
    for cand in ("pdftotext", "pdftotext.exe"):
        try:
            p = subprocess.run([cand, "-v"], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=10)
            exe = cand
            break
        except Exception:
            continue
    if not exe:
        raise RuntimeError("pdftotext not found")
    p = subprocess.run([exe, "-layout", "-enc", "UTF-8", path, "-"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=120)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or b"").decode("utf-8", "replace")[:300])
    chunks = p.stdout.decode("utf-8", "replace").split("\f")
    pages = []
    for i, chunk in enumerate(chunks):
        if i == len(chunks) - 1 and not chunk.strip():
            break
        pages.append({"page": i + 1, "text": norm_ws(chunk), "blocks": []})
    return pages, {"extractor": "pdftotext", "pages": len(pages)}


_OBJ_RE = re.compile(rb"<<(.*?)>>\s*stream\r?\n", re.S)
_STR_RE = re.compile(rb"\((?:\\.|[^\\()])*\)")


def _pdf_unescape(b):
    out, i = [], 0
    while i < len(b):
        c = b[i:i + 1]
        if c == b"\\" and i + 1 < len(b):
            n = b[i + 1:i + 2]
            mp = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b",
                  b"f": b"\f", b"(": b"(", b")": b")", b"\\": b"\\"}
            if n in mp:
                out.append(mp[n]); i += 2; continue
            m = re.match(rb"[0-7]{1,3}", b[i + 1:i + 4])
            if m:
                out.append(bytes([int(m.group(0), 8) & 0xFF])); i += 1 + len(m.group(0)); continue
            i += 2; continue
        out.append(c); i += 1
    return b"".join(out)


def _pdf_pages_minimal(path):
    """Last-resort extractor: inflate content streams and pull Tj/TJ literals.

    It cannot decode CID fonts, so callers must treat the output as partial.
    """
    data = open(path, "rb").read()
    texts = []
    for m in _OBJ_RE.finditer(data):
        head = m.group(1)
        start = m.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        body = data[start:end]
        if b"FlateDecode" in head:
            try:
                body = zlib.decompress(body)
            except Exception:
                continue
        if b"Tj" not in body and b"TJ" not in body:
            continue
        line = []
        for s in _STR_RE.findall(body):
            raw = _pdf_unescape(s[1:-1])
            try:
                line.append(raw.decode("utf-8"))
            except Exception:
                line.append(raw.decode("latin-1", "replace"))
        if line:
            texts.append("".join(line))
    text = norm_ws("\n".join(texts))
    pages = [{"page": 1, "text": text, "blocks": []}] if text else []
    return pages, {"extractor": "stdlib-minimal", "pages": len(pages),
                   "warning": "CID fonts are not decoded; treat as partial"}


def pdf_pages(path):
    errors = []
    for fn in (_pdf_pages_pymupdf, _pdf_pages_pdftotext, _pdf_pages_minimal):
        try:
            pages, meta = fn(path)
            if pages and any(p["text"] for p in pages):
                meta["errors"] = errors
                return pages, meta
            errors.append("%s: no text" % fn.__name__)
        except Exception as exc:
            errors.append("%s: %s: %s" % (fn.__name__, type(exc).__name__, exc))
    return [], {"extractor": None, "pages": 0, "errors": errors}


# --------------------------------------------------------------------------
# Case loading / material discovery
# --------------------------------------------------------------------------
def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            for s in walk_strings(v):
                yield s
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            for s in walk_strings(v):
                yield s


def load_case(path):
    if path and os.path.exists(path):
        try:
            return jload(path), os.path.abspath(path)
        except Exception as exc:
            return {"_case_read_error": "%s: %s" % (type(exc).__name__, exc)}, os.path.abspath(path)
    return {}, os.path.abspath(path) if path else ""


CONTROL_NAMES = frozenset(("case.json", "task.md", "draft.json", "plan.json",
                           "glossary.json", "result.json", "report.md"))


def find_materials(case, case_path, input_dir, exts=TEXT_EXT + PDF_EXT,
                   skip_names=CONTROL_NAMES):
    """Return absolute paths named in the case, then any matching file in input.

    An explicit mention wins; a directory scan is the fallback.  Order is
    preserved and duplicates removed.  Harness control files are skipped so a
    case.json never becomes the "source document".
    """
    base = os.path.dirname(case_path) if case_path else input_dir
    found = []
    for s in walk_strings(case):
        low = s.lower().strip()
        if not low.endswith(exts):
            continue
        if os.path.basename(low) in skip_names:
            continue
        for cand in (s, os.path.join(base, s), os.path.join(input_dir, s)):
            if os.path.isfile(cand):
                found.append(os.path.abspath(cand))
                break
    if os.path.isdir(input_dir):
        for root, _dirs, files in os.walk(input_dir):
            for name in sorted(files):
                if name.lower().endswith(exts) and name.lower() not in skip_names:
                    found.append(os.path.abspath(os.path.join(root, name)))
    seen, out = set(), []
    for p in found:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def file_kind(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return "pdf"
    if ext in (".json", ".jsonl"):
        return "json"
    if ext in (".csv", ".tsv"):
        return "csv"
    if ext in (".bib",):
        return "bib"
    if ext in (".ris",):
        return "ris"
    if ext in (".tex",):
        return "tex"
    if ext in (".yaml", ".yml"):
        return "yaml"
    return "text"


INLINE_KEYS = ("material", "materials", "source_text", "source", "text",
               "content", "document", "passage", "abstract", "manuscript",
               "paper", "input_text", "paragraphs")


def inline_materials(case):
    """Cases sometimes embed the prose instead of pointing at a file.

    Only explicit content keys are considered, and only strings long enough to
    be prose, so the task description itself never becomes the "source".
    """
    chunks = []

    def take(v):
        for s in walk_strings(v):
            t = (s or "").strip()
            if len(t) >= 120 and not t.lower().endswith(TEXT_EXT + PDF_EXT):
                chunks.append(t)

    if isinstance(case, dict):
        for k, v in case.items():
            if str(k).lower() in INLINE_KEYS and not isinstance(v, (int, float, bool)):
                take(v)
    if not chunks:
        return []
    text = "\n\n".join(chunks)
    return [{"path": "", "name": "case-inline-material", "kind": "text",
             "text": text, "pages": [], "meta": {"inline": True}}]


def material_texts(case, case_path, input_dir, exts=TEXT_EXT + PDF_EXT):
    """[{path, name, kind, text, pages, meta}] for every material file."""
    out = []
    for path in find_materials(case, case_path, input_dir, exts):
        kind = file_kind(path)
        if kind == "pdf":
            pages, meta = pdf_pages(path)
            text = "\n\n".join(p["text"] for p in pages if p.get("text"))
            out.append({"path": path, "name": os.path.basename(path), "kind": "pdf",
                        "text": text, "pages": pages, "meta": meta})
        else:
            try:
                text = read_text(path)
            except Exception as exc:
                out.append({"path": path, "name": os.path.basename(path), "kind": kind,
                            "text": "", "pages": [], "meta": {"error": str(exc)}})
                continue
            out.append({"path": path, "name": os.path.basename(path), "kind": kind,
                        "text": text, "pages": [], "meta": {}})
    if not out or not any(m["text"].strip() for m in out):
        inline = inline_materials(case)
        if inline:
            out.extend(inline)
    return out


def case_id_of(case, files):
    if isinstance(case, dict):
        for k in ("case_id", "caseId", "id", "slug", "name"):
            v = case.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    if files:
        return os.path.splitext(os.path.basename(files[0]))[0]
    return "unknown-case"


def sources_of(files):
    out = []
    for p in files:
        try:
            out.append({"file": os.path.basename(p), "sha256": sha256_file(p),
                        "bytes": os.path.getsize(p)})
        except OSError:
            out.append({"file": os.path.basename(p), "sha256": None, "bytes": None})
    return out


# --------------------------------------------------------------------------
# output_contract
# --------------------------------------------------------------------------
def contract_fields(case):
    """Normalise the many shapes an output_contract can take into a list."""
    if not isinstance(case, dict):
        return []
    oc = case.get("output_contract")
    if oc is None:
        oc = case.get("outputContract")
    if oc is None:
        return []
    if isinstance(oc, list):
        out = []
        for x in oc:
            if isinstance(x, (str, int)):
                out.append(str(x))
            elif isinstance(x, dict):
                for k in ("name", "key", "field", "id"):
                    if isinstance(x.get(k), str):
                        out.append(x[k])
                        break
        return out
    if isinstance(oc, dict):
        for key in ("fields", "required", "properties", "keys"):
            v = oc.get(key)
            if isinstance(v, list):
                return [str(x) for x in v]
            if isinstance(v, dict):
                return [str(x) for x in v.keys()]
        return [str(k) for k in oc.keys()]
    return []


_SYNONYMS = [
    ("case_id", ("case",)),
    ("status", ("status", "state")),
    ("translation", ("translat", "target_text", "译文")),
    ("segments", ("segment", "paragraph", "bilingual", "align", "段")),
    ("glossary", ("glossar", "terminolog", "term", "术语")),
    ("checks", ("check", "issue", "problem", "diagnos", "lint", "error", "consist")),
    ("references", ("reference", "bibliograph", "citation", "文献")),
    ("notes", ("note", "summary", "card", "摘要", "笔记")),
    ("outline", ("outline", "提纲", "slide")),
    ("graph", ("graph", "node", "edge", "triple", "知识图谱")),
    ("assertions", ("assert", "claim", "nanopub", "断言")),
    ("latex", ("latex", "tex", "code")),
    ("tables", ("table", "param", "参数")),
    ("sections", ("section", "chapter", "章节")),
    ("edited_text", ("edited", "polished", "revised", "rewritten", "润色")),
    ("edits", ("edit", "change", "diff", "修改")),
    ("text", ("text", "content", "markdown", "正文")),
    ("files", ("file", "artifact", "output")),
    ("metrics", ("metric", "score", "stat")),
]


def _norm_key(s):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", str(s).lower()).strip("_")


def resolve_contract(fields, payload, alias=None):
    """Map requested contract names onto values we actually computed.

    Exact key match wins; then an explicit alias table; then a conservative
    synonym match.  Anything unresolved becomes None and is reported, never
    guessed silently.
    """
    alias = alias or {}
    keys = {_norm_key(k): k for k in payload.keys()}
    out, missing, via = {}, [], {}
    for f in fields:
        nf = _norm_key(f)
        if f in payload:
            out[f] = payload[f]; via[f] = "exact"; continue
        if nf in keys:
            out[f] = payload[keys[nf]]; via[f] = "normalised"; continue
        if f in alias and alias[f] in payload:
            out[f] = payload[alias[f]]; via[f] = "alias"; continue
        hit = None
        for target, needles in _SYNONYMS:
            if any(n in nf for n in needles) and target in payload:
                hit = target
                break
        if hit is not None:
            out[f] = payload[hit]; via[f] = "synonym:" + hit
        else:
            out[f] = None
            missing.append(f)
    return out, missing, via


# --------------------------------------------------------------------------
# text segmentation
# --------------------------------------------------------------------------
_HEAD_RE = re.compile(
    r"^\s*(?:#{1,6}\s+|(?:\d+(?:\.\d+)*)[.)]?\s+|[IVX]+\.\s+|"
    r"(?:Abstract|ABSTRACT|摘要|Introduction|INTRODUCTION|引言|"
    r"Methods?|METHODS?|Results?|RESULTS?|Discussion|DISCUSSION|"
    r"Conclusion|CONCLUSION|References|REFERENCES|参考文献)\b)")
_SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[\"'])")
_CJK_END = re.compile(r"(?<=[。！？；])\s*")


def split_paragraphs(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", text)
    out = []
    for b in blocks:
        b = norm_ws(b)
        if b:
            out.append(b)
    if not out and text.strip():
        out = [norm_ws(text)]
    return out


def split_sentences(text):
    t = one_line(text)
    if not t:
        return []
    parts = []
    for chunk in _CJK_END.split(t):
        if not chunk:
            continue
        parts.extend(p for p in _SENT_END.split(chunk) if p)
    return [p.strip() for p in parts if p.strip()]


def is_heading(line):
    s = (line or "").strip()
    if not s or len(s) > 90:
        return False
    if _HEAD_RE.match(s):
        return True
    if s.endswith(":") and len(s) < 60:
        return True
    return False


def segments(paragraphs, prefix="p"):
    """Stable IDs: p001, p002 ...; sentences get p001.s01."""
    out = []
    for i, para in enumerate(paragraphs, 1):
        pid = "%s%03d" % (prefix, i)
        sents = split_sentences(para)
        out.append({"id": pid, "text": para,
                    "sentences": [{"id": "%s.s%02d" % (pid, j), "text": s}
                                  for j, s in enumerate(sents, 1)]})
    return out


def anchor(page, para, start=None, end=None):
    a = "p%s#p%s" % (page, para)
    if start is not None:
        a += "@%d-%d" % (start, end if end is not None else start)
    return a


def parse_anchor(a):
    m = re.match(r"p(\d+)#p([A-Za-z0-9_.-]+)(?:@(\d+)-(\d+))?$", a or "")
    if not m:
        return None
    return {"page": int(m.group(1)), "para": m.group(2),
            "start": int(m.group(3)) if m.group(3) else None,
            "end": int(m.group(4)) if m.group(4) else None}


# --------------------------------------------------------------------------
# numbers / units / citations / terms
# --------------------------------------------------------------------------
_NUM_RE = re.compile(
    r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?(?:\s?[%％])?"
    r"(?:\s?(?:mg|g|kg|ug|µg|ml|mL|L|mmol|mol|µmol|mM|nM|nm|mm|cm|km|m|"
    r"s|ms|min|h|hr|hours?|days?|weeks?|months?|years?|"
    r"°C|K|Pa|kPa|MPa|bar|atm|Hz|kHz|MHz|GHz|"
    r"GB|MB|KB|TB|bp|kb|Da|kDa|W|kW|V|mV|mA|A|J|kJ|cal|kcal|"
    r"px|dpi|fps|FLOPs?|GFLOPs?|TFLOPS?|B|M|K))?(?![\w])"
)


def numbers(text):
    out = []
    for m in _NUM_RE.finditer(text or ""):
        raw = m.group(0).strip()
        if not raw or re.fullmatch(r"[-+]?\d+", raw) and len(raw) > 1 and raw.startswith("0"):
            pass
        out.append({"raw": raw, "span": [m.start(), m.end()]})
    return out


def number_multiset(text):
    from collections import Counter
    c = Counter()
    for n in numbers(text):
        c[re.sub(r"\s+", "", n["raw"])] += 1
    return c


_CITE_RE = re.compile(
    r"\[(\d+(?:\s*[,–\-]\s*\d+)*)\]"          # [1] [2,4] [3-5]
    r"|\\cite[a-zA-Z*]*\{([^}]+)\}"           # \cite{a,b}
    r"|\(([A-Z][A-Za-z\-]+(?:\s+et\s+al\.?)?,\s*\d{4}[a-z]?(?:;\s*[A-Z][A-Za-z\-]+(?:\s+et\s+al\.?)?,\s*\d{4}[a-z]?)*)\)"
)


def citations(text):
    out = []
    for m in _CITE_RE.finditer(text or ""):
        if m.group(1):
            ids = []
            for part in re.split(r",", m.group(1)):
                part = part.strip()
                rng = re.match(r"(\d+)\s*[–-]\s*(\d+)$", part)
                if rng:
                    a, b = int(rng.group(1)), int(rng.group(2))
                    if 0 < b - a <= 30:
                        ids.extend(str(x) for x in range(a, b + 1))
                elif part.isdigit():
                    ids.append(part)
            out.append({"style": "numeric", "ids": ids, "raw": m.group(0),
                        "span": [m.start(), m.end()]})
        elif m.group(2):
            out.append({"style": "latex", "ids": [x.strip() for x in m.group(2).split(",") if x.strip()],
                        "raw": m.group(0), "span": [m.start(), m.end()]})
        else:
            out.append({"style": "author-year", "ids": [m.group(3)],
                        "raw": m.group(0), "span": [m.start(), m.end()]})
    return out


def citation_ids(text):
    out = []
    for c in citations(text):
        out.extend(c["ids"])
    return out


def norm_key(s):
    s = (s or "").lower()
    s = re.sub(r"[\s\-_/]+", " ", s)
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def similarity(a, b):
    return difflib.SequenceMatcher(None, norm_key(a), norm_key(b)).ratio()


def term_candidates(text, min_count=2, max_terms=200):
    """Acronyms + repeated capitalised phrases; a starting point, not truth."""
    from collections import Counter
    c = Counter()
    for m in re.finditer(r"\b([A-Z][A-Za-z0-9\-]{1,}(?:\s+[A-Z][A-Za-z0-9\-]{1,}){0,4})\b", text or ""):
        t = m.group(1).strip()
        if len(t) < 3 or len(t) > 60:
            continue
        c[t] += 1
    for m in re.finditer(r"\b([A-Z]{2,6})\b", text or ""):
        c[m.group(1)] += 1
    return [{"term": t, "count": n} for t, n in c.most_common(max_terms) if n >= min_count]


def check_quote(quote, source):
    """Return (ok, start, end) for a quote against a source text.

    Whitespace and curly-quote differences are tolerated; wording is not.
    """
    q = one_line(quote)
    s = one_line(source)
    if not q:
        return False, None, None
    idx = s.find(q)
    if idx >= 0:
        return True, idx, idx + len(q)
    # tolerate hyphenation at line breaks and quote style
    q2 = q.replace("’", "'").replace("“", '"').replace("”", '"')
    s2 = s.replace("’", "'").replace("“", '"').replace("”", '"')
    idx = s2.find(q2)
    if idx >= 0:
        return True, idx, idx + len(q2)
    return False, None, None


# --------------------------------------------------------------------------
# result envelope
# --------------------------------------------------------------------------
def write_result(out_dir, skill, task, case, status, main_result,
                 evidence=None, uncertainty=None, sources=None,
                 contract_alias=None, runs=None, artifacts=None):
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    payload = dict(main_result or {})
    payload.setdefault("case_id", case.get("case_id") if isinstance(case, dict) else None)
    payload.setdefault("status", status)
    payload.setdefault("evidence", evidence or {})
    payload.setdefault("uncertainty", uncertainty or {})
    payload.setdefault("sources", sources or [])
    fields = contract_fields(case)
    values, missing, via = resolve_contract(fields, payload, contract_alias)
    # case_id is always present even when the contract does not ask for it
    case_id = payload.get("case_id") or case_id_of(case, [])
    result = {
        "schema": SCHEMA,
        "skill": skill,
        "skill_version": "1.0.0",
        "case_id": case_id,
        "task": task,
        "status": status,
        "main_result": main_result,
        "evidence": evidence or {},
        "uncertainty": uncertainty or {},
        "sources": sources or [],
        "output_contract": values,
        "output_contract_fields": fields,
        "contract_resolution": via,
        "contract_unresolved": missing,
        "runs": runs or [],
    }
    jdump(os.path.join(out_dir, "result.json"), result)
    return result


def write_report(out_dir, title, lines):
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    body = ["# " + title, ""] + list(lines) + [""]
    with io.open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8",
                 newline="\n") as fh:
        fh.write("\n".join(body))


def rel(out_dir, path):
    try:
        return os.path.relpath(path, out_dir).replace("\\", "/")
    except ValueError:
        return os.path.basename(path)


def load_draft(path):
    if not path:
        return None
    if not os.path.exists(path):
        return None
    try:
        return jload(path)
    except Exception:
        return {"raw": read_text(path)}


def find_draft(case, case_path, input_dir, names=("draft.json", "answer.json",
                                                  "translations.json", "edits.json",
                                                  "graph.json", "assertions.json")):
    """Look for a model-authored draft the harness may have written."""
    if isinstance(case, dict):
        for k in ("draft", "draft_path", "answer_path", "submission"):
            v = case.get(k)
            if isinstance(v, str):
                for cand in (v, os.path.join(os.path.dirname(case_path), v),
                             os.path.join(input_dir, v)):
                    if os.path.isfile(cand):
                        return os.path.abspath(cand)
    work_dirs = [os.environ.get("SKILL_WORK") or "", "/app/work",
                 os.path.join(os.getcwd(), "work")]
    for n in names:
        for wd in work_dirs:
            if not wd:
                continue
            cand = os.path.join(wd, n)
            if os.path.isfile(cand):
                return os.path.abspath(cand)
        for cand in (os.path.join(input_dir, n),
                     os.path.join(os.path.dirname(case_path), n)):
            if os.path.isfile(cand):
                return os.path.abspath(cand)
    return None


def ascii_print(*args):
    try:
        print(*args)
    except UnicodeEncodeError:
        print(" ".join(str(a).encode("ascii", "replace").decode("ascii") for a in args))
