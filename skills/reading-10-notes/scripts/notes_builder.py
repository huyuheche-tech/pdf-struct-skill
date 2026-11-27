# -*- coding: utf-8 -*-
"""notes_builder -- turn a paper into an anchored, checkable note card.

The model writes the note content; this module owns everything that must be
deterministic:

  * section splitting with stable ids (s01, s02, ...) and paragraph ids
    (s01.p01, s01.p02, ...) plus character offsets;
  * anchor resolution: every quote in a card field must be findable in the
    paragraph the anchor points at;
  * field completeness (research question / data / method / findings /
    limitations), findings count, limitations count;
  * knowledge-point de-duplication (normalised similarity > 0.90);
  * section coverage by section summaries;
  * a markdown note plus JSON artefacts.

It never invents a note.  Without a draft it emits a candidate card clearly
marked ``candidate: true`` and reports ``partial``.
"""
from __future__ import print_function

import os
import re

import skillkit as sk

FIELDS = ("research_question", "data", "method", "findings", "limitations")
DUP_THRESHOLD = 0.90

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
_ANCHOR_RE = re.compile(r"^(s\d+)\s*\.\s*(p\d+)(?:\s*@\s*(\d+)\s*-\s*(\d+))?$", re.I)


# --------------------------------------------------------------------------
# section splitting
# --------------------------------------------------------------------------
def _title_of_numbered(num, title):
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
        title = _title_of_numbered(m.group(1), m.group(2))
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
    """Split into sections; each paragraph gets sNN.pMM, text, start, end."""
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
            "text": sk.norm_ws(body),
            "start": start,
            "end": start + len(body),
        })

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
        s.pop("paragraphs_text", None)
    return sections


def build_index(sections):
    idx = {}
    for s in sections:
        for p in s["paragraphs"]:
            idx[p["id"]] = p
    return idx


def resolve_anchor(anchor, index):
    m = _ANCHOR_RE.match((anchor or "").strip())
    if not m:
        return None, None
    pid = "s%02d.p%02d" % (int(m.group(1)[1:]), int(m.group(2)[1:]))
    return index.get(pid), pid


def top_level_sections(sections):
    if not sections:
        return []
    low = min(s["level"] for s in sections)
    return [s for s in sections if s["level"] == low]


# --------------------------------------------------------------------------
# anchors
# --------------------------------------------------------------------------
def anchors_of(item):
    out = []
    if isinstance(item, dict):
        if item.get("anchor") is not None or item.get("quote") is not None:
            out.append({"anchor": item.get("anchor"), "quote": item.get("quote")})
        for a in item.get("anchors") or []:
            if isinstance(a, dict):
                out.append({"anchor": a.get("anchor"), "quote": a.get("quote")})
    return out


def check_one_anchor(a, index):
    """Return (ok, detail, resolved_span)."""
    anchor = a.get("anchor")
    quote = a.get("quote") or ""
    if not anchor:
        return False, "no anchor given", None
    para, pid = resolve_anchor(anchor, index)
    if para is None:
        return False, "anchor %r does not match any paragraph" % str(anchor)[:40], None
    if not quote.strip():
        return False, "anchor %s has an empty quote" % pid, None
    ok, s, e = sk.check_quote(quote, para["text"])
    if not ok:
        return False, "quote not found in %s: %r" % (pid, sk.one_line(quote)[:60]), None
    return True, "", {"paragraph_id": pid, "start": para["start"] + s,
                      "end": para["start"] + e}


def validate_card(card, index, errors):
    """Field presence + per-field anchors.  Returns per-field completeness."""
    complete = {}
    for f in ("research_question", "data", "method"):
        v = card.get(f)
        ok = isinstance(v, dict) and bool(str(v.get("text") or "").strip())
        complete[f] = ok
        if not ok:
            errors.append({"code": "field_missing", "field": f,
                           "detail": "card.%s is missing or has no text" % f})
            continue
        for a in anchors_of(v):
            ok_a, detail, _ = check_one_anchor(a, index)
            if not ok_a:
                errors.append({"code": "anchor_unresolved", "field": f,
                               "detail": detail})

    findings = card.get("findings")
    if not isinstance(findings, list):
        complete["findings"] = False
        errors.append({"code": "field_missing", "field": "findings",
                       "detail": "card.findings is missing"})
        findings = []
    elif len(findings) < 2:
        complete["findings"] = False
        errors.append({"code": "findings_thin", "field": "findings",
                       "detail": "only %d finding(s); at least 2 required" % len(findings)})
    else:
        complete["findings"] = True
    for i, it in enumerate(findings, 1):
        if not isinstance(it, dict):
            errors.append({"code": "field_missing", "field": "findings",
                           "detail": "finding %d is not an object" % i})
            continue
        if not str(it.get("text") or "").strip():
            errors.append({"code": "field_missing", "field": "findings",
                           "detail": "finding %d has no text" % i})
        for a in anchors_of(it):
            ok_a, detail, _ = check_one_anchor(a, index)
            if not ok_a:
                errors.append({"code": "anchor_unresolved", "field": "findings",
                               "id": "finding-%d" % i, "detail": detail})
        if not anchors_of(it):
            errors.append({"code": "anchor_unresolved", "field": "findings",
                           "id": "finding-%d" % i, "detail": "no anchor given"})

    lims = card.get("limitations")
    if not isinstance(lims, list):
        complete["limitations"] = False
        errors.append({"code": "field_missing", "field": "limitations",
                       "detail": "card.limitations is missing"})
        errors.append({"code": "limitations_missing", "field": "limitations",
                       "detail": "no limitation stated"})
        lims = []
    elif not lims:
        complete["limitations"] = False
        errors.append({"code": "limitations_missing", "field": "limitations",
                       "detail": "limitations list is empty"})
    else:
        complete["limitations"] = True
    for i, it in enumerate(lims, 1):
        if not isinstance(it, dict):
            continue
        if not str(it.get("text") or "").strip():
            errors.append({"code": "field_missing", "field": "limitations",
                           "detail": "limitation %d has no text" % i})
        for a in anchors_of(it):
            ok_a, detail, _ = check_one_anchor(a, index)
            if not ok_a:
                errors.append({"code": "anchor_unresolved", "field": "limitations",
                               "id": "limitation-%d" % i, "detail": detail})
        if not anchors_of(it):
            errors.append({"code": "anchor_unresolved", "field": "limitations",
                           "id": "limitation-%d" % i, "detail": "no anchor given"})
    return complete


def validate_knowledge(points, index, errors):
    seen = []
    n_dup = 0
    for i, p in enumerate(points, 1):
        if not isinstance(p, dict):
            continue
        text = str(p.get("text") or "").strip()
        if not text:
            errors.append({"code": "field_missing", "field": "knowledge_points",
                           "id": "kp-%d" % i, "detail": "knowledge point has no text"})
            continue
        for j, prev in enumerate(seen, 1):
            if sk.similarity(text, prev) > DUP_THRESHOLD:
                errors.append({"code": "duplicate_point", "field": "knowledge_points",
                               "id": "kp-%d" % i,
                               "detail": "similar to kp-%d (%.2f)" % (j, sk.similarity(text, prev))})
                n_dup += 1
                break
        seen.append(text)
        for a in anchors_of(p):
            ok_a, detail, _ = check_one_anchor(a, index)
            if not ok_a:
                errors.append({"code": "anchor_unresolved", "field": "knowledge_points",
                               "id": "kp-%d" % i, "detail": detail})
        if not anchors_of(p):
            errors.append({"code": "anchor_unresolved", "field": "knowledge_points",
                           "id": "kp-%d" % i, "detail": "no anchor given"})
    return n_dup


def validate_summaries(summaries, sections, index, errors, warnings):
    tops = top_level_sections(sections)
    by_id = {s["id"]: s for s in sections}
    given = {}
    for i, sm in enumerate(summaries, 1):
        if not isinstance(sm, dict):
            continue
        sid = str(sm.get("section_id") or "").strip()
        if sid not in by_id:
            # tolerate a section title instead of an id
            hit = [s["id"] for s in sections if s["title"].strip().lower() == sid.lower()]
            if hit:
                sid = hit[0]
            else:
                warnings.append({"code": "section_unknown",
                                 "detail": "section_summaries[%d] refers to %r" % (i, sid)})
                continue
        given[sid] = sm
        if not str(sm.get("text") or "").strip():
            errors.append({"code": "field_missing", "field": "section_summaries",
                           "id": sid, "detail": "summary text is empty"})
        anchors = anchors_of(sm)
        if not anchors:
            errors.append({"code": "summary_unanchored", "field": "section_summaries",
                           "id": sid, "detail": "summary has no anchor"})
            continue
        for a in anchors:
            ok_a, detail, _ = check_one_anchor(a, index)
            if not ok_a:
                errors.append({"code": "anchor_unresolved", "field": "section_summaries",
                               "id": sid, "detail": detail})
    covered = []
    for s in tops:
        if s["id"] in given:
            covered.append(s["id"])
        else:
            errors.append({"code": "section_uncovered", "field": "section_summaries",
                           "id": s["id"],
                           "detail": "no summary for top-level section %r" % s["title"]})
    return covered


# --------------------------------------------------------------------------
# candidate extraction (no draft)
# --------------------------------------------------------------------------
CUES = {
    "research_question": (r"we (?:propose|study|investigate|address|examine|ask|test|evaluate)",
                          r"this (?:paper|study|work)", r"here we",
                          r"本文", r"我们(?:提出|研究|考察|关注|探讨)"),
    "data": (r"dataset", r"data set", r"corpus", r"benchmark", r"participants",
             r"samples", r"数据", r"数据集", r"样本", r"受试者"),
    "method": (r"we (?:train|use|apply|fine-tune|fine tune|optimize)",
               r"our (?:method|model|approach|framework)", r"algorithm",
               r"算法", r"方法", r"模型"),
    "findings": (r"results? (?:show|indicate|suggest)", r"we (?:find|found|observe)",
                 r"improv(?:e|es|ed)", r"outperform", r"reduc(?:e|es|ed)",
                 r"表明", r"显示", r"提升", r"降低", r"优于"),
    "limitations": (r"limitation", r"future work", r"does not", r"cannot",
                    r"局限", r"不足", r"尚未", r"未来工作"),
}


def candidate_card(sections):
    """Cheap cue-based candidates; every item is marked candidate=true."""
    card = {f: [] for f in FIELDS}
    for s in sections:
        for p in s["paragraphs"]:
            for sent in sk.split_sentences(p["text"]):
                low = sent.lower()
                for f, pats in CUES.items():
                    if len(card[f]) >= (2 if f == "findings" else 1):
                        continue
                    if any(re.search(pat, low, re.I) for pat in pats):
                        card[f].append({"text": sent, "anchor": p["id"],
                                        "quote": sent, "candidate": True})
    out = {}
    for f in ("research_question", "data", "method"):
        items = card[f]
        out[f] = ({"text": items[0]["text"], "anchor": items[0]["anchor"],
                   "quote": items[0]["quote"], "candidate": True}
                  if items else {"text": "", "anchor": "", "quote": "", "candidate": True})
    out["findings"] = card["findings"]
    out["limitations"] = card["limitations"]
    return out


def candidate_summaries(sections):
    out = []
    for s in sections:
        if not s["paragraphs"]:
            continue
        p = s["paragraphs"][0]
        sents = sk.split_sentences(p["text"])
        out.append({"section_id": s["id"],
                    "text": sents[0] if sents else p["text"][:120],
                    "anchor": p["id"],
                    "quote": sents[0] if sents else p["text"][:120],
                    "candidate": True})
    return out


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def _cell(s, limit=200):
    s = sk.one_line(s).replace("|", "\\|")
    return s if len(s) <= limit else s[:limit - 1] + "…"


def _field_text(v):
    if isinstance(v, dict):
        return str(v.get("text") or "")
    return str(v or "")


def render_notes_md(title, card, summaries, points, sections, errors, status):
    lines = ["# 论文笔记：%s" % title, "",
             "> status: **%s**；章节 %d 个；硬错误 %d 条。" % (status, len(sections), len(errors)),
             "> 锚点格式 `sNN.pMM`（段落）或 `sNN.pMM@start-end`（段内字符区间）。", "",
             "## 论文卡片", "",
             "| 字段 | 内容 | 锚点 | 证据 |", "|---|---|---|---|"]
    for f, label in (("research_question", "研究问题"), ("data", "数据"),
                     ("method", "方法")):
        v = card.get(f) if isinstance(card.get(f), dict) else {}
        lines.append("| %s | %s | %s | %s |" % (label, _cell(_field_text(v)),
                                                 _cell(v.get("anchor"), 40),
                                                 _cell(v.get("quote"), 120)))
    for f, label in (("findings", "发现"), ("limitations", "局限")):
        items = card.get(f) or []
        if not items:
            lines.append("| %s | （空） | — | — |" % label)
        for i, it in enumerate(items, 1):
            it = it if isinstance(it, dict) else {}
            lines.append("| %s %d | %s | %s | %s |" % (
                label, i, _cell(it.get("text")), _cell(it.get("anchor"), 40),
                _cell(it.get("quote"), 120)))

    lines += ["", "## 逐节摘要", "", "| 章节 | 标题 | 摘要 | 锚点 |", "|---|---|---|---|"]
    smap = {str(s.get("section_id")): s for s in summaries if isinstance(s, dict)}
    for s in sections:
        sm = smap.get(s["id"]) or {}
        lines.append("| %s | %s | %s | %s |" % (s["id"], _cell(s["title"], 40),
                                                _cell(sm.get("text")), _cell(sm.get("anchor"), 40)))
    lines += ["", "## 知识点", "", "| # | 知识点 | 锚点 |", "|---|---|---|"]
    if not points:
        lines.append("| — | （空） | — |")
    for i, p in enumerate(points, 1):
        p = p if isinstance(p, dict) else {}
        lines.append("| kp-%d | %s | %s |" % (i, _cell(p.get("text")), _cell(p.get("anchor"), 40)))
    if errors:
        lines += ["", "## 待修问题", ""]
        for e in errors[:30]:
            lines.append("- `%s` %s %s" % (e.get("code"), e.get("field") or "",
                                           e.get("detail") or ""))
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# main run
# --------------------------------------------------------------------------
def pick_source(prose, case):
    """An explicitly named material wins; otherwise the longest text wins."""
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


def run(case, materials, out_dir, draft_path=None, title=None):
    prose = [m for m in materials if m["kind"] in ("text", "pdf") and m["text"].strip()]
    if not prose:
        prose = [m for m in materials if m["kind"] == "json" and m["text"].strip()]
    if not prose:
        main = {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
                "notes": "", "sections": [], "card": {},
                "checks": {"errors": [{"code": "no_material",
                                       "detail": "no readable text material"}],
                           "warnings": []},
                "metrics": {"sections": 0, "covered": 0, "fields_complete": 0,
                            "field_coverage": 0.0, "anchors_resolved": 0,
                            "anchor_total": 0, "anchor_resolution_rate": 0.0,
                            "duplicates": 0}}
        return {"status": "failed", "main": main, "warnings": [],
                "errors": [{"code": "no_material", "field": "", "detail": "no readable text material"}]}

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
                             "detail": "draft is not a JSON object; candidate card used"})
        card = candidate_card(sections)
        points = [{"text": it["text"], "anchor": it["anchor"], "quote": it["quote"],
                   "candidate": True}
                  for f in ("findings", "limitations") for it in card.get(f, [])][:4]
        summaries = candidate_summaries(sections)
        complete = {f: bool(card.get(f)) for f in FIELDS}
        covered = [s["id"] for s in top_level_sections(sections) if s["paragraphs"]]
        # a candidate card is a hand-off, not a checked note
        warnings.append({"code": "candidate_card",
                         "detail": "no draft supplied; cue-based candidates are unverified"})
    else:
        card = draft.get("card") if isinstance(draft.get("card"), dict) else {}
        points = draft.get("knowledge_points") or []
        summaries = draft.get("section_summaries") or []
        if not isinstance(points, list):
            points = []
        if not isinstance(summaries, list):
            summaries = []
        complete = validate_card(card, index, errors)
        validate_knowledge(points, index, errors)
        covered = validate_summaries(summaries, sections, index, errors, warnings)

    tops = top_level_sections(sections)
    # anchor resolution statistics over everything the card claims
    total_anchors, resolved = 0, 0
    for f in ("research_question", "data", "method"):
        for a in anchors_of(card.get(f) if isinstance(card.get(f), dict) else {}):
            total_anchors += 1
            ok, _, _ = check_one_anchor(a, index)
            resolved += 1 if ok else 0
    for f in ("findings", "limitations"):
        for it in card.get(f) or []:
            for a in anchors_of(it):
                total_anchors += 1
                ok, _, _ = check_one_anchor(a, index)
                resolved += 1 if ok else 0
    dup_count = sum(1 for e in errors if e["code"] == "duplicate_point")
    fields_complete = sum(1 for f in FIELDS if complete.get(f))

    hard = len(errors)
    if candidate:
        status = "partial"
    elif hard:
        status = "partial"
    else:
        status = "success"

    md = render_notes_md(doc_title, card, summaries, points, sections, errors, status)
    with open(os.path.join(out_dir, "notes.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)

    checks = {"errors": errors, "warnings": warnings,
              "summary": {"n_sections": len(sections), "n_top_sections": len(tops),
                          "n_errors": len(errors), "n_warnings": len(warnings),
                          "candidate": candidate}}
    sk.jdump(os.path.join(out_dir, "checks.json"), checks)

    notes_json = {"title": doc_title, "candidate": candidate, "card": card,
                  "section_summaries": summaries, "knowledge_points": points,
                  "fields_complete": [f for f in FIELDS if complete.get(f)]}
    sk.jdump(os.path.join(out_dir, "notes.json"), notes_json)

    metrics = {
        "sections": len(sections),
        "covered": len(covered),
        "fields_complete": fields_complete,
        "field_coverage": round(fields_complete / 5.0, 3),
        "anchors_resolved": resolved,
        "anchor_total": total_anchors,
        "anchor_resolution_rate": (round(resolved / total_anchors, 3)
                                   if total_anchors else 0.0),
        "duplicates": dup_count,
    }
    main = {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
            "notes": md,
            "sections": [{"id": s["id"], "title": s["title"], "level": s["level"],
                          "start": s["start"], "end": s["end"],
                          "paragraphs": [{"id": p["id"], "start": p["start"],
                                          "end": p["end"], "chars": len(p["text"])}
                                         for p in s["paragraphs"]]}
                         for s in sections],
            "card": card,
            "checks": checks,
            "metrics": metrics,
            "files": {"notes": "notes.md", "notes_json": "notes.json",
                      "sections": "sections.json", "checks": "checks.json"}}
    return {"status": status, "main": main, "errors": errors, "warnings": warnings,
            "candidate": candidate, "sources": [m["path"] for m in materials],
            "sections": sections}
