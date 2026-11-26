# -*- coding: utf-8 -*-
"""intro_builder -- deterministic evidence ledger for an introduction section.

The model writes the prose; this module does what a language model must not be
trusted with:

  * a sentence-level evidence table with stable anchors (pNNN.sNN) built from
    the supplied abstract / results / notes;
  * a four-part structure check (background / related work / gap / contributions);
  * a number-to-evidence check (every number in the draft must be traceable);
  * a contribution-to-quote binding check (each contribution needs a quote that
    can still be found in the materials);
  * citation presence, gap strength, related-work grouping, and -- when a
    bibliography is supplied -- key existence.

It never invents prose.  With no draft it writes the evidence table and a
hand-off instruction, and marks the result "partial".
"""
from __future__ import print_function

import json
import os
import re

import skillkit as sk

# --- citation markers accepted in the draft -------------------------------
BRACKET_KEY = re.compile(
    r"\[([A-Za-z][A-Za-z0-9_:.\-]*(?:\s*[,;]\s*[A-Za-z][A-Za-z0-9_:.\-]*)*)\]")
LATEX_CITE = re.compile(r"\\cite[a-zA-Z*]*\{([^}]+)\}")
AUTHOR_YEAR = re.compile(
    r"\(([A-Z][A-Za-z\-]+)(?:\s+et\s+al\.?)?(?:\s+and\s+[A-Z][A-Za-z\-]+)?"
    r",\s*(\d{4}[a-z]?)\)")
NUMERIC_CITE = re.compile(r"\[\d+(?:\s*[,–\-]\s*\d+)*\]")

SECTIONS = ("background", "related_work", "gap", "contributions")
SECTION_LABEL = {"background": "Background", "related_work": "Related Work",
                 "gap": "Gap", "contributions": "Contributions"}

COMPARE = re.compile(
    r"\b(?:improv|outperform|higher|lower|increase|decrease|reduce|gain|"
    r"compared|versus|relative to|better|worse|significant|p\s*<)\w*", re.I)
COMPARE_ZH = re.compile(r"(?:提升|降低|优于|相比|显著|增益|下降|提高|减少|对比)")
CONCLUSION = re.compile(
    r"\b(?:suggest|indicat|show|demonstrat|conclud|find|observ|reveal)\w*", re.I)
CONCLUSION_ZH = re.compile(r"(?:表明|说明|提示|发现|显示|证明|结论)")


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def prose_materials(materials):
    return [m for m in materials
            if m.get("kind") in ("text", "pdf") and (m.get("text") or "").strip()]


def full_text(prose):
    return "\n\n".join(m["text"] for m in prose)


def is_claim_sentence(sentence):
    if sk.numbers(sentence):
        return True
    if COMPARE.search(sentence) or COMPARE_ZH.search(sentence):
        return True
    if CONCLUSION.search(sentence) or CONCLUSION_ZH.search(sentence):
        return True
    return False


def build_evidence(prose):
    """All claim-bearing sentences, with stable anchors and their numbers."""
    text = full_text(prose)
    paras = [p for p in sk.split_paragraphs(text) if p]
    segs = sk.segments(paras)
    rows = []
    for para in segs:
        for sent in para["sentences"]:
            if not is_claim_sentence(sent["text"]):
                continue
            rows.append({
                "anchor": sent["id"],
                "text": sent["text"],
                "numbers": [n["raw"] for n in sk.numbers(sent["text"])],
            })
    return rows, text


# --------------------------------------------------------------------------
# citations
# --------------------------------------------------------------------------
def citation_spans(text):
    spans = []
    for rx in (BRACKET_KEY, LATEX_CITE, AUTHOR_YEAR, NUMERIC_CITE):
        for m in rx.finditer(text or ""):
            spans.append([m.start(), m.end()])
    return spans


def parse_citations(text):
    out = []
    for m in BRACKET_KEY.finditer(text or ""):
        keys = [k.strip() for k in re.split(r"[,;]", m.group(1)) if k.strip()]
        out.append({"style": "key", "keys": keys, "raw": m.group(0),
                    "span": [m.start(), m.end()]})
    for m in LATEX_CITE.finditer(text or ""):
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        out.append({"style": "key", "keys": keys, "raw": m.group(0),
                    "span": [m.start(), m.end()]})
    for m in AUTHOR_YEAR.finditer(text or ""):
        out.append({"style": "author-year", "keys": [m.group(1)],
                    "surname": m.group(1), "year": m.group(2),
                    "raw": m.group(0), "span": [m.start(), m.end()]})
    out.sort(key=lambda c: c["span"][0])
    return out


def strip_spans(text, spans):
    if not spans:
        return text
    out, last = [], 0
    for a, b in sorted(spans):
        if a < last:
            continue
        out.append(text[last:a])
        last = b
    out.append(text[last:])
    return "".join(out)


def number_tokens(text):
    spans = citation_spans(text)
    clean = strip_spans(text, spans)
    return [re.sub(r"\s+", "", n["raw"]).lower() for n in sk.numbers(clean)]


# --------------------------------------------------------------------------
# bibliography
# --------------------------------------------------------------------------
_BIB_ENTRY = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.S)
_BIB_FIELD = re.compile(r"(\w+)\s*=\s*[\{\"](.+?)[\}\"]\s*,?\s*\n", re.S)


def _surname(author_field):
    if not author_field:
        return ""
    first = author_field.split(" and ")[0].strip()
    if "," in first:
        return first.split(",")[0].strip()
    parts = first.split()
    return parts[-1] if parts else ""


def load_library(materials):
    """Return {key: {surname, year, title}} from .bib / .json materials."""
    lib = {}
    for m in materials:
        kind = m.get("kind")
        if kind == "bib":
            text = m.get("text") or ""
            for ent in _BIB_ENTRY.finditer(text):
                key = ent.group(2).strip()
                body = text[ent.end():ent.end() + 1200]
                fields = {f.group(1).lower(): f.group(2).strip()
                          for f in _BIB_FIELD.finditer(body)}
                lib[key] = {"surname": _surname(fields.get("author", "")),
                            "year": (fields.get("year", "") or "").strip(),
                            "title": fields.get("title", "")}
        elif kind == "json":
            try:
                obj = json.loads(m.get("text") or "")
            except Exception:
                continue
            rows = []
            if isinstance(obj, dict):
                if isinstance(obj.get("references"), list):
                    rows = obj["references"]
                elif isinstance(obj.get("library"), list):
                    rows = obj["library"]
                else:
                    for k, v in obj.items():
                        if isinstance(v, dict):
                            v = dict(v)
                            v.setdefault("key", k)
                            rows.append(v)
            elif isinstance(obj, list):
                rows = obj
            for r in rows:
                if not isinstance(r, dict):
                    continue
                key = r.get("key") or r.get("id") or r.get("citekey")
                if not key:
                    continue
                author = r.get("author") or r.get("authors") or ""
                if isinstance(author, list):
                    author = " and ".join(str(a) for a in author)
                lib[str(key)] = {
                    "surname": r.get("surname") or _surname(str(author)),
                    "year": str(r.get("year") or ""),
                    "title": r.get("title") or "",
                }
    return lib


def author_year_match(cite, lib):
    surname = sk.norm_key(cite.get("surname", ""))
    year = str(cite.get("year", ""))
    for entry in lib.values():
        if sk.norm_key(entry.get("surname", "")) == surname and \
                str(entry.get("year", "")).startswith(year[:4]):
            return True
    return False


# --------------------------------------------------------------------------
# draft normalisation
# --------------------------------------------------------------------------
def _section_text(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("text") or "").strip()
    if isinstance(value, list):
        return "\n".join(str(v) for v in value if str(v).strip()).strip()
    return ""


def _section_aj(value):
    return bool(isinstance(value, dict) and value.get("author_judgment"))


def normalise_draft(draft):
    d = draft if isinstance(draft, dict) else {}
    sec = d.get("sections") if isinstance(d.get("sections"), dict) else {}
    out = {}
    for name in SECTIONS:
        out[name] = _section_text(sec.get(name))
    aj = set(x for x in (d.get("author_judgment") or []) if isinstance(x, str))
    for name in SECTIONS:
        if _section_aj(sec.get(name)):
            aj.add(name)
    return out, aj, (d.get("contribution_evidence") or []), (d.get("groups") or [])


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------
def validate(sections, author_judgment, contrib_evidence, groups, evidence,
             material_text, lib):
    errors, warnings = [], []
    anchors = {e["anchor"] for e in evidence}

    # 1. four sections present and non-empty
    for name in SECTIONS:
        if not sections.get(name):
            errors.append({"code": "section_missing", "section": name,
                           "detail": "section %r is empty or absent" % name})

    # 2. citation presence per section (or explicit author judgement)
    for name in SECTIONS:
        text = sections.get(name) or ""
        if not text:
            continue
        cites = parse_citations(text)
        if not cites and name not in author_judgment:
            errors.append({"code": "citation_missing", "section": name,
                           "detail": "no citation marker and no author_judgment"})

    # 3. every number in the draft must exist in the evidence table
    evidence_tokens = set()
    for e in evidence:
        for raw in e["numbers"]:
            evidence_tokens.add(re.sub(r"\s+", "", raw).lower())
    n_claims, supported = 0, 0
    for name in SECTIONS:
        text = sections.get(name) or ""
        for tok in number_tokens(text):
            n_claims += 1
            if tok in evidence_tokens:
                supported += 1
            else:
                errors.append({"code": "claim_unsupported", "section": name,
                               "detail": "number %r is not in the evidence table" % tok})

    # 4. contribution <-> evidence binding
    by_index = {}
    for row in contrib_evidence:
        if isinstance(row, dict) and row.get("contribution") is not None:
            try:
                by_index[int(row["contribution"])] = row
            except (TypeError, ValueError):
                continue
    contributions = [c for c in (sections.get("contributions") or "").split("\n")
                     if c.strip()] if sections.get("contributions") else []
    n_contrib = max(len(contributions), (max(by_index) if by_index else 0))
    bound = 0
    for i in range(1, n_contrib + 1):
        row = by_index.get(i)
        quote = (row or {}).get("quote") or ""
        if not row:
            errors.append({"code": "contribution_unbound", "contribution": i,
                           "detail": "contribution %d has no contribution_evidence" % i})
            continue
        ok, _s, _e = sk.check_quote(quote, material_text)
        if not ok:
            errors.append({"code": "contribution_unbound", "contribution": i,
                           "detail": "quote for contribution %d is not found in materials" % i})
            continue
        anchor = row.get("anchor")
        if anchor and anchor not in anchors:
            warnings.append({"code": "anchor_unlisted", "contribution": i,
                             "detail": "anchor %r is not in the evidence table; quote still matched"
                                       % anchor})
        bound += 1

    # 5. gap needs at least two distinct citations
    gap_keys = set()
    for c in parse_citations(sections.get("gap") or ""):
        gap_keys.update(c["keys"])
    if sections.get("gap") and len(gap_keys) < 2:
        errors.append({"code": "gap_unsupported", "detail":
                       "gap cites %d distinct work(s); at least 2 are required" % len(gap_keys)})

    # 6. related work grouping
    if not isinstance(groups, list) or len(groups) < 2:
        errors.append({"code": "grouping_thin", "detail":
                       "related work needs >=2 labelled groups, got %d"
                       % (len(groups) if isinstance(groups, list) else 0)})
    else:
        for i, g in enumerate(groups, 1):
            label = (g.get("label") if isinstance(g, dict) else "") or ""
            works = (g.get("works") if isinstance(g, dict) else None) or []
            if not str(label).strip() or not [w for w in works if str(w).strip()]:
                errors.append({"code": "grouping_thin", "group": i,
                               "detail": "group %d needs a non-empty label and >=1 work" % i})

    # 7. citation keys must exist in the supplied bibliography
    n_citations = 0
    if lib:
        for name in SECTIONS:
            text = sections.get(name) or ""
            for c in parse_citations(text):
                n_citations += 1
                if c["style"] == "author-year":
                    if not author_year_match(c, lib):
                        errors.append({"code": "citation_unknown", "section": name,
                                       "detail": "author-year %r matches no library entry"
                                                 % c["raw"]})
                else:
                    for key in c["keys"]:
                        if key not in lib:
                            errors.append({"code": "citation_unknown", "section": name,
                                           "detail": "citation key %r not in bibliography" % key})
        for i, g in enumerate(groups if isinstance(groups, list) else [], 1):
            for w in (g.get("works") if isinstance(g, dict) else []) or []:
                if str(w).strip() and str(w) not in lib:
                    errors.append({"code": "citation_unknown", "group": i,
                                   "detail": "group work %r not in bibliography" % w})
    else:
        for name in SECTIONS:
            n_citations += len(parse_citations(sections.get(name) or ""))
        if n_citations:
            warnings.append({"code": "citation_unverified",
                             "detail": "no bibliography supplied; citation keys were not resolved"})

    metrics = {"n_claims": n_claims, "supported": supported,
               "contributions": n_contrib, "bound": bound,
               "groups": len(groups) if isinstance(groups, list) else 0,
               "citations": n_citations}
    return errors, warnings, metrics


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def render(sections, groups, title):
    lines = ["# %s" % (title or "Introduction"), ""]
    for name in ("background", "related_work"):
        lines.append("## %s" % SECTION_LABEL[name])
        lines.append(sections.get(name) or "_(not written)_")
        lines.append("")
        if name == "related_work" and isinstance(groups, list):
            for g in groups:
                if not isinstance(g, dict):
                    continue
                lines.append("### %s" % (g.get("label") or "(unnamed group)"))
                for w in g.get("works") or []:
                    lines.append("- %s" % w)
                lines.append("")
    for name in ("gap", "contributions"):
        lines.append("## %s" % SECTION_LABEL[name])
        text = sections.get(name) or ""
        if name == "contributions" and text:
            for i, c in enumerate([x for x in text.split("\n") if x.strip()], 1):
                lines.append("%d. %s" % (i, c.strip()))
        else:
            lines.append(text or "_(not written)_")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------
def run(case, materials, out_dir, draft_path=None):
    prose = prose_materials(materials)
    if not prose:
        return {"status": "failed", "main": {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
                                             "checks": {"errors": [{"code": "no_material"}],
                                                        "warnings": []}},
                "errors": [{"code": "no_material"}], "warnings": [],
                "sources": [m["path"] for m in materials]}

    evidence, material_text = build_evidence(prose)
    sk.jdump(os.path.join(out_dir, "evidence.json"),
             {"n_evidence": len(evidence), "evidence": evidence})

    draft = sk.load_draft(draft_path)
    has_draft = isinstance(draft, dict) and isinstance(draft.get("sections"), dict)
    sections, aj, contrib_evidence, groups = normalise_draft(draft if has_draft else {}) \
        if has_draft else ({n: "" for n in SECTIONS}, set(), [], [])
    lib = load_library(materials)

    if has_draft:
        errors, warnings, metrics = validate(sections, aj, contrib_evidence, groups,
                                             evidence, material_text, lib)
    else:
        errors = [{"code": "section_missing", "section": n,
                   "detail": "section %r is empty or absent" % n} for n in SECTIONS]
        warnings = []
        metrics = {"n_claims": 0, "supported": 0, "contributions": 0, "bound": 0,
                   "groups": 0, "citations": 0}

    status = "partial" if (not has_draft or errors) else "success"
    md = render(sections, groups, (case or {}).get("title") if isinstance(case, dict) else None)
    with open(os.path.join(out_dir, "intro.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)

    checks = {"errors": errors, "warnings": warnings,
              "summary": {"n_errors": len(errors), "n_warnings": len(warnings),
                          "sections": {n: bool(sections.get(n)) for n in SECTIONS},
                          "metrics": metrics}}
    sk.jdump(os.path.join(out_dir, "checks.json"), checks)

    main = {
        "case_id": sk.case_id_of(case, [m["path"] for m in materials]),
        "status": status,
        "sections": {n: sections.get(n, "") for n in SECTIONS},
        "evidence": evidence,
        "checks": checks,
        "metrics": metrics,
        "files": {"intro": "intro.md", "evidence": "evidence.json",
                  "checks": "checks.json"},
    }
    return {"status": status, "main": main, "errors": errors, "warnings": warnings,
            "has_draft": has_draft,
            "sources": [m["path"] for m in materials]}
