# -*- coding: utf-8 -*-
"""nanopub_builder -- split a paper into atomic, evidence-bound assertions.

The model writes the assertions; this module owns the deterministic part:

  * section/paragraph ids (sNN.pMM) reused from the note pipeline;
  * evidence resolution: every quote must exist in the paragraph it cites;
  * triple completeness and a controlled predicate vocabulary;
  * atomicity (no un-split ``;``, no ``and`` joining two predicates);
  * condition retention (under / when / only if / 在…条件下);
  * over-broad claims (all / always / never / every) without support;
  * duplicate assertions (normalised similarity > 0.90);
  * source metadata (source_id + paragraph_id);
  * export in assertion / provenance / pubinfo form with stable URNs.

It never invents an assertion.  Without a draft it emits sentence-level
candidates marked ``candidate: true`` and reports ``partial``.
"""
from __future__ import print_function

import hashlib
import os
import re

import skillkit as sk

PREDICATES = ("supports", "contradicts", "uses", "compares",
              "has_property", "measured_by", "part_of")
DUP_THRESHOLD = 0.90
MAX_EVIDENCE = 400

HEAD_WORDS = (
    r"abstract|introduction|related work|background|motivation|"
    r"materials and methods|methods?|methodology|experiments?|"
    r"results?|discussion|conclusions?|limitations?|future work|"
    r"摘要|引言|绪论|相关工作|背景|方法|材料与方法|实验|结果|讨论|结论|局限|不足"
)
_MD_HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_NUM_HEAD = re.compile(r"^(\d+(?:\.\d+)*)[.)、]?\s+(\S.*)$")
_NAMED_HEAD = re.compile(r"^(%s)\s*[:：]?$" % HEAD_WORDS, re.I)
_INLINE_HEAD = re.compile(r"^(%s)\s*[.。:：]\s+(\S.*)$" % HEAD_WORDS, re.I)
_ANCHOR_RE = re.compile(r"^(s\d+)\s*\.\s*(p\d+)$", re.I)
COND_RE = re.compile(
    r"\b(?:under|when|whenever|only if|in the setting of|conditional on|provided that)\b"
    r"|在.{0,20}(?:条件|情况|场景)下|当.{0,25}时|仅当|只有在", re.I)
ABS_EN = ("all", "always", "never", "every", "everyone", "everything")
ABS_ZH = ("所有", "全部", "总是", "从不", "每个", "一律", "必然")
VERB_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|has|have|had|"
    r"increase[sd]?|decrease[sd]?|reduce[sd]?|improve[sd]?|lower(?:s|ed)?|"
    r"raise[sd]?|outperform[s]?|use[sd]?|show[s]?|find[s]?|require[sd]?|"
    r"contain[s]?|lead[s]?|remain[s]?|affect[s]?|predict[s]?|achieved?|"
    r"achieve[sd]?|reach(?:es|ed)?|gain[s]?|add[s]?|lift(?:s|ed)?|cost[s]?|"
    r"boost(?:s|ed)?|drop(?:s|ped)?|cut[s]?|help(?:s|ed)?|differ(?:s|ed)?|"
    r"work(?:s|ed)?|confirm(?:s|ed)?|support(?:s|ed)?|suggest(?:s|ed)?)\b", re.I)


# --------------------------------------------------------------------------
# section splitting (same contract as the notes skill)
# --------------------------------------------------------------------------
def _title_of_numbered(title):
    title = title.strip()
    if not title or len(title) > 60:
        return None
    if title.endswith((".", "。", "，", ",", ";")):
        return None
    if not re.match(r"^[A-Z\u4e00-\u9fff]", title):
        return None
    if len(title.split()) > 8:
        return None
    return title


def heading_of(line):
    s = (line or "").strip()
    if not s or len(s) > 100:
        return None
    m = _MD_HEAD.match(s)
    if m:
        return {"level": len(m.group(1)), "title": m.group(2).strip()}
    m = _NAMED_HEAD.match(s)
    if m:
        return {"level": 1, "title": s.rstrip(":：").strip()}
    m = _NUM_HEAD.match(s)
    if m:
        title = _title_of_numbered(m.group(2))
        if title:
            return {"level": m.group(1).count(".") + 1, "title": title}
    return None


def _blocks(text):
    out, pos = [], 0
    for m in re.finditer(r"\n[ \t]*\n+", text):
        out.append((text[pos:m.start()], pos))
        pos = m.end()
    out.append((text[pos:], pos))
    return out


def build_sections(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    sections, cur = [], None

    def new_section(title, level, start):
        sec = {"id": "s%02d" % (len(sections) + 1), "title": title,
               "level": level, "start": start, "end": None, "paragraphs": []}
        sections.append(sec)
        return sec

    def add_para(sec, body, hint):
        body = body.strip()
        if not body:
            return
        start = text.find(body, max(0, hint))
        if start < 0:
            start = text.find(body)
        if start < 0:
            start = max(0, hint)
        sec["paragraphs"].append({
            "id": "%s.p%02d" % (sec["id"], len(sec["paragraphs"]) + 1),
            "text": sk.norm_ws(body), "start": start, "end": start + len(body)})

    for block, boff in _blocks(text):
        if not block.strip():
            continue
        lines = block.split("\n")
        i = 0
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            continue
        line = lines[i]
        head = heading_of(line)
        if head is None:
            inline = _INLINE_HEAD.match(line.strip())
            if inline and len(inline.group(1)) <= 30:
                head = {"level": 1, "title": inline.group(1).strip()}
                if cur is not None and cur["end"] is None:
                    cur["end"] = boff
                cur = new_section(head["title"], 1, boff)
                add_para(cur, "\n".join([inline.group(2)] + lines[i + 1:]), boff)
                continue
        if head:
            if cur is not None and cur["end"] is None:
                cur["end"] = boff
            cur = new_section(head["title"], head["level"], boff)
            rest = "\n".join(lines[i + 1:]).strip()
            if rest:
                add_para(cur, rest, boff)
            continue
        if cur is None:
            cur = new_section("Body", 1, boff)
        add_para(cur, block, boff)

    total = len(text)
    for s in sections:
        if s["end"] is None:
            s["end"] = total
        s["n_paragraphs"] = len(s["paragraphs"])
    return sections


def build_index(sections):
    idx = {}
    for s in sections:
        for p in s["paragraphs"]:
            idx[p["id"]] = p
    return idx


def norm_pid(pid):
    m = _ANCHOR_RE.match((pid or "").strip())
    if not m:
        return None
    return "s%02d.p%02d" % (int(m.group(1)[1:]), int(m.group(2)[1:]))


def pick_source(prose, case):
    if isinstance(case, dict):
        for k in ("material", "source", "paper", "file", "materials"):
            v = case.get(k)
            names = v if isinstance(v, list) else [v]
            for n in names:
                if not isinstance(n, str) or not n.strip():
                    continue
                base = os.path.basename(n.strip())
                for m in prose:
                    if m["name"] == base:
                        return m
    return max(prose, key=lambda m: len(m["text"]))


# --------------------------------------------------------------------------
# assertion checks
# --------------------------------------------------------------------------
def atomicity(text):
    """Return (is_atomic, reason)."""
    t = (text or "").strip()
    if ";" in t or "；" in t:
        return False, "un-split semicolon"
    if re.search(r"并且|同时|以及|而且", t):
        return False, "CJK conjunction joining two predicates"
    if re.search(r"\band\s+(?:it|they|this|these|those|we|he|she)\b", t, re.I):
        return False, "'and' introduces a second subject"
    parts = re.split(r"\band\b", t, flags=re.I)
    if len(parts) >= 2:
        verbed = [p for p in parts if VERB_RE.search(p)]
        if len(verbed) >= 2:
            return False, "'and' joins two predicates"
    return True, ""


def absolute_terms(text):
    low = " " + (text or "").lower() + " "
    hits = [w for w in ABS_EN if re.search(r"\b%s\b" % w, low)]
    hits += [w for w in ABS_ZH if w in (text or "")]
    return hits


def sentence_of(para_text, evidence):
    sents = sk.split_sentences(para_text)
    q = sk.norm_key(evidence)
    if not q:
        return para_text
    for s in sents:
        n = sk.norm_key(s)
        if q in n or (n and n in q):
            return s
    return para_text


def span_in_para(evidence, para):
    q = (evidence or "").strip()
    if not q:
        return None
    i = para["text"].find(q)
    if i >= 0:
        return [para["start"] + i, para["start"] + i + len(q)]
    ok, a, b = sk.check_quote(q, para["text"])
    if ok:
        return [para["start"] + a, para["start"] + b]
    return None


def locate(evidence, paragraph_id, index, full_text):
    """Return (ok, pid, span, warning)."""
    pid = norm_pid(paragraph_id) if paragraph_id else None
    warn = ""
    if pid and pid in index:
        para = index[pid]
        ok, _s, _e = sk.check_quote(evidence, para["text"])
        if ok:
            return True, pid, span_in_para(evidence, para), ""
        # fall through to a global search so a wrong paragraph is reported, not hidden
        if sk.check_quote(evidence, full_text)[0]:
            return True, pid, None, "evidence found elsewhere; paragraph_id looks wrong"
        return False, pid, None, ""
    ok, _s, _e = sk.check_quote(evidence, full_text)
    if ok:
        return True, pid or "", None, "paragraph_id not found; evidence matched the full text"
    return False, pid or "", None, ""


def validate_assertion(a, index, full_text, errors, warnings, claimed):
    aid = str(a.get("id") or "a?")
    text = str(a.get("text") or "").strip()
    evidence = str(a.get("evidence") or "").strip()
    subject = str(a.get("subject") or "").strip()
    pred = str(a.get("predicate") or "").strip().lower()
    obj = str(a.get("object") or "").strip()
    conds = str(a.get("conditions") or "").strip()
    src = str(a.get("source_id") or "").strip()
    pid_raw = str(a.get("paragraph_id") or "").strip()

    if not src or not pid_raw:
        errors.append({"code": "source_missing", "id": aid,
                       "detail": "source_id and paragraph_id are both required"})

    if not evidence:
        errors.append({"code": "evidence_unresolved", "id": aid,
                       "detail": "no evidence quote"})
        ok_ev, pid, span = False, norm_pid(pid_raw), None
    elif len(evidence) > MAX_EVIDENCE:
        errors.append({"code": "evidence_too_long", "id": aid,
                       "detail": "%d chars; keep evidence <= %d" % (len(evidence), MAX_EVIDENCE)})
        ok_ev, pid, span, _w = locate(evidence, pid_raw, index, full_text)
    else:
        ok_ev, pid, span, warn = locate(evidence, pid_raw, index, full_text)
        if warn:
            warnings.append({"code": "evidence_elsewhere", "id": aid, "detail": warn})
        if not ok_ev:
            errors.append({"code": "evidence_unresolved", "id": aid,
                           "detail": "quote not found in %s" % (pid_raw or "the material")})

    if not (subject and pred and obj):
        errors.append({"code": "triple_incomplete", "id": aid,
                       "detail": "subject/predicate/object must all be non-empty"})
    if pred and pred not in PREDICATES:
        errors.append({"code": "predicate_invalid", "id": aid,
                       "detail": "%r not in %s" % (pred, "/".join(PREDICATES))})

    ok_atomic, why = atomicity(text)
    if not ok_atomic:
        errors.append({"code": "not_atomic", "id": aid, "detail": why})

    if ok_ev and pid and pid in index:
        sent = sentence_of(index[pid]["text"], evidence)
        if COND_RE.search(sent) and not conds:
            errors.append({"code": "condition_dropped", "id": aid,
                           "detail": "source sentence states a condition; conditions is empty"})
    elif ok_ev and COND_RE.search(evidence) and not conds:
        errors.append({"code": "condition_dropped", "id": aid,
                       "detail": "evidence states a condition; conditions is empty"})

    claim_abs = absolute_terms(text)
    if claim_abs and not absolute_terms(evidence):
        errors.append({"code": "overbroad", "id": aid,
                       "detail": "claim uses %s but the evidence does not" % "/".join(claim_abs)})

    for prev_id, prev_text in claimed:
        sim = sk.similarity(text, prev_text)
        if sim > DUP_THRESHOLD:
            errors.append({"code": "duplicate_assertion", "id": aid,
                           "detail": "similar to %s (%.2f)" % (prev_id, sim)})
            break
    claimed.append((aid, text))
    return {"id": aid, "pid": pid or pid_raw, "ok_evidence": ok_ev, "span": span}


# --------------------------------------------------------------------------
# candidate splitting (no draft)
# --------------------------------------------------------------------------
def split_compound(sent):
    pieces = re.split(r"[;；]", sent)
    out = []
    for piece in pieces:
        for part in re.split(r"\bwhile\b|\bwhereas\b", piece, flags=re.I):
            part = part.strip()
            if not part:
                continue
            chunks = re.split(r"\band\b", part, flags=re.I)
            if len(chunks) >= 2 and len([c for c in chunks if VERB_RE.search(c)]) >= 2:
                out.extend(c.strip() for c in chunks if c.strip())
            else:
                out.append(part)
    return [p for p in out if p and len(p.split()) >= 4]


def candidate_assertions(sections, source_id):
    out = []
    for s in sections:
        for p in s["paragraphs"]:
            for sent in sk.split_sentences(p["text"]):
                for piece in split_compound(sent):
                    if len(out) >= 40:
                        return out
                    out.append({"id": "a%d" % (len(out) + 1), "text": piece,
                                "subject": "", "predicate": "", "object": "",
                                "conditions": "", "evidence": piece,
                                "source_id": source_id, "paragraph_id": p["id"],
                                "confidence": "low", "candidate": True})
    return out


# --------------------------------------------------------------------------
# export + rendering
# --------------------------------------------------------------------------
def urn_for(text, source_id):
    raw = ("%s|%s" % (text or "", source_id or "")).encode("utf-8")
    return "urn:nanopub:" + hashlib.sha256(raw).hexdigest()[:16]


def build_nanopub(assertions, case, source_name, index):
    entries, prov = [], []
    doi = (case.get("doi") if isinstance(case, dict) else None) or ""
    created = (case.get("created") if isinstance(case, dict) else None) or "unknown"
    for a in assertions:
        text = str(a.get("text") or "")
        src = str(a.get("source_id") or source_name)
        uri = urn_for(text, src)
        entries.append({"id": a.get("id"), "uri": uri, "text": text,
                        "subject": a.get("subject") or "", "predicate": a.get("predicate") or "",
                        "object": a.get("object") or "", "conditions": a.get("conditions") or "",
                        "confidence": a.get("confidence") or "medium"})
        pid = norm_pid(a.get("paragraph_id"))
        span = span_in_para(a.get("evidence") or "", index[pid]) if pid in index else None
        prov.append({"assertion_id": a.get("id"), "source_id": src, "doi": doi,
                     "paragraph_id": a.get("paragraph_id") or "",
                     "quote": a.get("evidence") or "", "char_span": span})
    return {"assertion": {"assertions": entries},
            "provenance": prov,
            "pubinfo": {"creator": "nanopub-assertion-builder", "created": created,
                        "license": "CC-BY-4.0", "template": "nano-pub/1"}}


def render_md(title, assertions, checks, status):
    lines = ["# Nanopublication 断言：%s" % title, "",
             "> status: **%s**；断言 %d 条；硬错误 %d 条。" % (
                 status, len(assertions), len(checks["errors"])), "",
             "| id | 断言 | 证据 | 位置 | 置信度 |", "|---|---|---|---|---|"]
    for a in assertions:
        lines.append("| %s | %s | %s | %s | %s |" % (
            a.get("id"), _cell(a.get("text")), _cell(a.get("evidence")),
            _cell(a.get("paragraph_id"), 20), a.get("confidence") or ""))
    if assertions:
        lines += ["", "## 三段结构（assertion / provenance / pubinfo）", "",
                  "| 断言 | URI | 主语 | 谓语 | 宾语 | 条件 |", "|---|---|---|---|---|---|"]
        for a in assertions:
            lines.append("| %s | `%s` | %s | %s | %s | %s |" % (
                a.get("id"), urn_for(a.get("text") or "", a.get("source_id") or ""),
                _cell(a.get("subject"), 40), a.get("predicate") or "",
                _cell(a.get("object"), 60), _cell(a.get("conditions"), 60)))
    if checks["errors"]:
        lines += ["", "## 待修问题", ""]
        for e in checks["errors"][:30]:
            lines.append("- `%s` %s: %s" % (e.get("code"), e.get("id"), e.get("detail")))
    return "\n".join(lines) + "\n"


def _cell(s, limit=120):
    s = sk.one_line(s).replace("|", "\\|")
    return s if len(s) <= limit else s[:limit - 1] + "…"


# --------------------------------------------------------------------------
# main run
# --------------------------------------------------------------------------
def run(case, materials, out_dir, draft_path=None, title=None):
    prose = [m for m in materials if m["kind"] in ("text", "pdf") and m["text"].strip()]
    if not prose:
        prose = [m for m in materials if m["kind"] == "json" and m["text"].strip()]
    if not prose:
        return {"status": "failed", "main": {}, "warnings": [], "errors": [],
                "fatal": [{"code": "no_material", "detail": "no readable text material"}]}

    source = pick_source(prose, case)
    text = source["text"]
    doc_title = title or (case.get("title") if isinstance(case, dict) else None) or source["name"]
    sections = build_sections(text)
    index = build_index(sections)
    sk.jdump(os.path.join(out_dir, "sections.json"),
             {"source": source["name"], "n_sections": len(sections), "sections": sections})

    draft = sk.load_draft(draft_path)
    errors, warnings = [], []
    candidate = False

    if not isinstance(draft, dict) or "raw" in draft:
        candidate = True
        if draft is not None:
            warnings.append({"code": "draft_unreadable",
                             "detail": "draft is not a JSON object; candidates used"})
        assertions = candidate_assertions(sections, source["name"])
        warnings.append({"code": "candidate_assertions",
                         "detail": "no draft supplied; sentence-level candidates are unverified"})
    else:
        raw = draft.get("assertions")
        assertions = [a for a in raw if isinstance(a, dict)] if isinstance(raw, list) else []
        if not assertions:
            warnings.append({"code": "no_assertions",
                             "detail": "draft has an empty assertions list"})
        claimed = []
        for a in assertions:
            validate_assertion(a, index, text, errors, warnings, claimed)

    hard = len(errors)
    if candidate or hard or not assertions:
        status = "partial"
    else:
        status = "success"

    checks = {"errors": errors, "warnings": warnings}
    sk.jdump(os.path.join(out_dir, "checks.json"), checks)
    nanopub = build_nanopub(assertions, case, source["name"], index)
    sk.jdump(os.path.join(out_dir, "nanopub.json"), nanopub)

    m = render_md(doc_title, assertions, checks, status)
    with open(os.path.join(out_dir, "assertions.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(m)

    n_ev = sum(1 for a in assertions if sk.check_quote(a.get("evidence") or "", text)[0] or
               (norm_pid(a.get("paragraph_id")) in index and
                sk.check_quote(a.get("evidence") or "",
                               index[norm_pid(a.get("paragraph_id"))]["text"])[0]))
    n_atomic = sum(1 for a in assertions if atomicity(a.get("text") or "")[0])
    n_over = sum(1 for e in errors if e["code"] == "overbroad")
    n_dup = sum(1 for e in errors if e["code"] == "duplicate_assertion")

    metrics = {"assertions": len(assertions), "evidence_resolved": n_ev,
               "atomic": n_atomic, "overbroad": n_over, "duplicates": n_dup}
    main = {"case_id": sk.case_id_of(case, [m2["path"] for m2 in materials]),
            "assertions": assertions,
            "nanopub": nanopub,
            "checks": checks,
            "metrics": metrics,
            "files": {"nanopub": "nanopub.json", "assertions": "assertions.md",
                      "checks": "checks.json", "sections": "sections.json"}}
    return {"status": status, "main": main, "errors": errors, "warnings": warnings,
            "candidate": candidate, "sources": [x["path"] for x in materials]}
