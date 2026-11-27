# -*- coding: utf-8 -*-
"""polish_ledger -- deterministic guard for academic language polishing.

The model does the rewriting; this module does everything that must not be
left to a language model:

  * sentence-level alignment between the manuscript and the polished draft
    (difflib on normalised sentences), so no sentence can vanish silently;
  * an edit ledger: every change needs a ``type`` and a ``reason``, and every
    ledger row must anchor back to the source text;
  * number / unit multiset equality (a polish may never move a number);
  * citation marker set equality;
  * hedge strength (may/suggest/indicate -> prove/demonstrate is an error);
  * negation polarity;
  * a locked term table (one spelling per term, no drift);
  * a high-confidence residual grammar lint (a/an, subject-verb, double space,
    sentence-initial lower case, ``et al`` without a period).

It never rewrites text by itself.  Without a draft it emits a plan and says so.
"""
from __future__ import print_function

import difflib
import io
import os
import re

import skillkit as sk

TYPES = ("grammar", "term", "tone", "clarity")
CHANGE_TYPES = ("grammar", "term", "tone", "clarity", "unchanged")

HEDGE_EN = re.compile(
    r"\b(?:may|might|could|suggest(?:s|ed|ing)?|indicat(?:e|es|ed|ing)|"
    r"likely|possibly)\b", re.I)
HEDGE_ZH = re.compile(r"(?:可能|或许|也许|大概|似乎|提示|倾向于|有望|推测)")
STRONG_EN = re.compile(
    r"\b(?:prov(?:e|es|en|ed)|demonstrat(?:e|es|ed|ing)|"
    r"show(?:s|n|ed)?\s+that|confirm(?:s|ed|ing)?|establish(?:es|ed|ing)?)\b", re.I)
STRONG_ZH = re.compile(r"(?:证明|证实|确证|表明事实|确立了|验证了)")

# ``不`` appears inside many neutral compounds (不同/不仅/不断); those are not
# negations and must not flip the polarity.
NEG_EN = re.compile(
    r"\b(?:not|no|never|none|neither|nor|cannot|without|"
    r"fail(?:s|ed)?\s+to|unable|isn't|aren't|wasn't|weren't|doesn't|don't|didn't)\b",
    re.I)
NEG_ZH = re.compile(
    r"(?:不(?!同|仅|但|过|断|论|管|如|久|少)|未|无(?!论)|非|没有|无法|不能|"
    r"并未|尚未|缺乏|否)")

DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s,;]+")
URL_RE = re.compile(r"https?://[^\s]+")

A_AN_EXC_A = frozenset((
    "university", "unique", "uniform", "universal", "user", "useful", "usual",
    "one", "once", "european", "ubiquitous", "unit", "union", "utility",
    "uranium", "eulogy", "ukulele"))
A_AN_EXC_AN = frozenset((
    "hour", "honest", "honor", "honour", "heir", "herb", "mba", "mri", "llm"))

SVA_VERBS = frozenset((
    "be", "have", "do", "make", "show", "use", "provide", "improve", "require",
    "indicate", "demonstrate", "suggest", "appear", "seem", "reduce", "increase",
    "lead", "give", "take", "allow", "cause", "remain", "occur", "represent",
    "include", "exhibit", "achieve", "confirm", "establish", "report", "offer",
    "need", "depend", "differ", "matter", "yield", "lower", "raise"))

LOWER_OK = frozenset((
    "eg", "ie", "etc", "vs", "cf", "al", "et", "fig", "eq", "no", "ref", "resp",
    "approx", "ca", "ibid", "vol", "pp", "p"))


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def norm(s):
    return re.sub(r"\s+", " ", (s or "").replace("\u00a0", " ")).strip()


def _strip_noise(text):
    """Remove spans whose digits are identifiers, not data."""
    spans = [(m.start(), m.end()) for m in DOI_RE.finditer(text or "")]
    spans += [(m.start(), m.end()) for m in URL_RE.finditer(text or "")]
    for c in sk.citations(text or ""):
        spans.append(tuple(c["span"]))
    out, last = [], 0
    for a, b in sorted(spans):
        if b <= last:
            continue
        out.append(text[last:a])
        last = b
    out.append(text[last:])
    return "".join(out)


def nums(text):
    from collections import Counter
    c = Counter()
    for n in sk.numbers(_strip_noise(text)):
        c[re.sub(r"\s+", "", n["raw"])] += 1
    return c


def cite_set(text):
    """Marker identity, normalised so [2,4] == [4,2]."""
    out = set()
    for c in sk.citations(text or ""):
        ids = sorted(set(c["ids"]))
        out.add("[%s]%s" % (",".join(ids), c["style"]))
    return out


def has_hedge(t):
    return bool(HEDGE_EN.search(t) or HEDGE_ZH.search(t))


def has_strong(t):
    return bool(STRONG_EN.search(t) or STRONG_ZH.search(t))


def has_neg(t):
    return bool(NEG_EN.search(t) or NEG_ZH.search(t))


def _ratio(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


# --------------------------------------------------------------------------
# glossary (same on-disk format as the translation skill)
# --------------------------------------------------------------------------
def load_glossary(case, materials):
    items, raw = [], None
    if isinstance(case, dict):
        for k in ("glossary", "terminology", "terms"):
            if isinstance(case.get(k), (list, dict)):
                raw = case[k]
                break
    if raw is None:
        for m in materials:
            if m["kind"] == "csv":
                rows = [r for r in m["text"].splitlines() if r.strip()]
                if not rows:
                    continue
                sep = "\t" if "\t" in rows[0] else ","
                head = [h.strip().lower() for h in rows[0].split(sep)]
                if not any(h in head for h in ("source", "term", "原文")):
                    continue
                si = head.index("source") if "source" in head else 0
                ti = 1
                for h in ("target", "translation", "canonical", "规范写法", "译名"):
                    if h in head:
                        ti = head.index(h)
                for r in rows[1:]:
                    cols = [c.strip() for c in r.split(sep)]
                    if len(cols) > max(si, ti) and cols[si]:
                        items.append({"source": cols[si], "target": cols[ti],
                                      "note": cols[2] if len(cols) > 2 else ""})
                break
            if m["kind"] == "json":
                try:
                    obj = sk.jload(m["path"])
                except Exception:
                    continue
                if isinstance(obj, dict):
                    obj = obj.get("glossary") or obj.get("terms") or []
                if isinstance(obj, list):
                    for it in obj:
                        if isinstance(it, dict) and it.get("source"):
                            items.append({"source": it["source"],
                                          "target": it.get("target") or "",
                                          "note": it.get("note") or ""})
                    if items:
                        break
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, dict):
                items.append({"source": k, "target": v.get("target") or "",
                              "note": v.get("note") or ""})
            else:
                items.append({"source": k, "target": str(v), "note": ""})
    elif isinstance(raw, list):
        for it in raw:
            if isinstance(it, dict) and it.get("source"):
                items.append({"source": it["source"],
                              "target": it.get("target") or "",
                              "note": it.get("note") or ""})
    seen = {}
    for it in items:
        k = sk.norm_key(it["source"])
        if not k:
            continue
        if k not in seen or (not seen[k]["target"] and it["target"]):
            seen[k] = {"source": it["source"].strip(),
                       "target": (it["target"] or "").strip(),
                       "note": (it.get("note") or "").strip()}
    return sorted(seen.values(), key=lambda x: -len(x["source"]))


# --------------------------------------------------------------------------
# alignment
# --------------------------------------------------------------------------
def align(src, ed):
    """Pair source and edited sentences; op in equal/replace/delete/insert."""
    S = [norm(x) for x in src]
    E = [norm(y) for y in ed]
    sm = difflib.SequenceMatcher(None, S, E, autojunk=False)
    rows = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rows.append({"src": i1 + k, "ed": j1 + k, "op": "equal"})
        elif tag == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                rows.append({"src": i1 + k, "ed": j1 + k, "op": "replace"})
            for k in range(i1 + n, i2):
                rows.append({"src": k, "ed": None, "op": "delete"})
            for k in range(j1 + n, j2):
                rows.append({"src": None, "ed": k, "op": "insert"})
        elif tag == "delete":
            for k in range(i1, i2):
                rows.append({"src": k, "ed": None, "op": "delete"})
        else:
            for k in range(j1, j2):
                rows.append({"src": None, "ed": k, "op": "insert"})
    return rows


def classify(src, ed, glossary):
    """Advisory change_type for one aligned pair (the ledger wins if present)."""
    a, b = norm(src), norm(ed)
    if a == b:
        return "unchanged"
    if re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]", "", a) == re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]", "", b):
        return "grammar"          # punctuation / spacing / capitalisation only
    if has_hedge(a) != has_hedge(b) or has_neg(a) != has_neg(b) or has_strong(a) != has_strong(b):
        return "tone"
    for g in glossary:
        if g["source"] and (g["source"].lower() in a.lower() or g["target"].lower() in b.lower()):
            return "term"
    wa, wb = len(a.split()), len(b.split())
    if wa and abs(wa - wb) / float(wa) > 0.18:
        return "clarity"
    return "grammar"


# --------------------------------------------------------------------------
# residual grammar lint (high confidence only)
# --------------------------------------------------------------------------
def lint_grammar(text):
    issues = []

    for m in re.finditer(r"\b([Aa]n?)\s+([A-Za-z][A-Za-z'\-]*)", text or ""):
        art, word = m.group(1), m.group(2)
        if re.search(r"\d", word):
            continue
        if any(ch.isupper() for ch in word[1:]):   # MRI, LED, mRNA: sound-based
            continue
        low = word.lower()
        starts_vowel = low[0] in "aeiou"
        if art.lower() == "a" and starts_vowel and low not in A_AN_EXC_A:
            issues.append({"rule": "a_an", "detail": "write 'an %s', not 'a %s'" % (word, word),
                           "span": [m.start(), m.end()]})
        elif art.lower() == "an" and not starts_vowel and low not in A_AN_EXC_AN:
            issues.append({"rule": "a_an", "detail": "write 'a %s', not 'an %s'" % (word, word),
                           "span": [m.start(), m.end()]})

    for m in re.finditer(r"(?:^|[.!?]\s+)(It|He|She)\s+(?:also\s+|often\s+|typically\s+)?"
                         r"([a-z]+)\b", text or ""):
        verb = m.group(2)
        if verb in SVA_VERBS:
            issues.append({"rule": "sva",
                           "detail": "'%s %s' needs third-person -s ('%ss')"
                                     % (m.group(1), verb, verb),
                           "span": [m.start(), m.end()]})

    for m in re.finditer(r"\S {2,}\S", text or ""):
        issues.append({"rule": "double_space",
                       "detail": "multiple spaces inside a line",
                       "span": [m.start(), m.end()]})

    for m in re.finditer(r"(?<=[.!?])\s+([a-z][A-Za-z']*)", text or ""):
        word = m.group(1)
        before = (text or "")[:m.start()].rstrip()
        tail = re.split(r"[\s(]", before)[-1].strip("()[],;:") if before else ""
        if tail.replace(".", "").lower() in LOWER_OK:      # e.g. / i.e. / Fig. / et al.
            continue
        if word.lower() in LOWER_OK:
            continue
        if len(word) == 1 and (text or "")[m.end():m.end() + 1] == ".":
            continue                                       # e.g. / i.e. mid-text
        if re.search(r"[A-Z]", word[1:]):
            continue
        issues.append({"rule": "lowercase_start",
                       "detail": "sentence starts with lower-case '%s'" % word,
                       "span": [m.start(), m.end()]})

    for m in re.finditer(r"\bet al(?!\.)", text or ""):
        issues.append({"rule": "etal_period", "detail": "'et al' needs a full stop",
                       "span": [m.start(), m.end()]})
    return issues


# --------------------------------------------------------------------------
# draft handling
# --------------------------------------------------------------------------
def draft_payload(draft):
    """Return (edited_text, ledger_rows).  Only these two shapes are accepted."""
    if not isinstance(draft, dict):
        return "", []
    text = draft.get("edited")
    if not isinstance(text, str) or not text.strip():
        text = draft.get("edited_text") if isinstance(draft.get("edited_text"), str) else ""
    rows = draft.get("edits") if isinstance(draft.get("edits"), list) else []
    return (text or ""), [r for r in rows if isinstance(r, dict)]


def _covering_row(led_edits, src_text, ed_text):
    """The ledger row that explains this aligned pair, if any."""
    for e in led_edits:
        o = norm(e.get("original"))
        n = norm(e.get("edited"))
        if o and o in norm(src_text) and (not n or n in norm(ed_text)):
            return e
    return None


def sentences_of(text):
    """Paragraph-aware sentence split (keeps a title out of the abstract)."""
    out = []
    for para in sk.split_paragraphs(text):
        out.extend(sk.split_sentences(para))
    return out


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def build_plan(source_name, sents, glossary):
    plan = []
    for i, s in enumerate(sents, 1):
        sid = "s%02d" % i
        hits = [{"source": g["source"], "target": g["target"]} for g in glossary
                if g["source"] and g["source"].lower() in s.lower()]
        plan.append({"id": sid, "sentence": s,
                     "locked_terms": hits,
                     "numbers": [n["raw"] for n in sk.numbers(s)],
                     "citations": [c["raw"] for c in sk.citations(s)]})
    return {"source": source_name, "n_sentences": len(sents),
            "glossary": glossary, "sentences": plan,
            "instruction": ("Write draft.json as {\"edited\": \"<full polished text>\", "
                            "\"edits\": [{\"id\":\"s01\",\"original\":\"...\","
                            "\"edited\":\"...\",\"type\":\"grammar|term|tone|clarity\","
                            "\"reason\":\"...\"}]}. Every changed sentence needs a ledger row "
                            "with a type and a reason. Never touch numbers, citation markers, "
                            "negation or hedge strength.")}


SKIP_PROSE = frozenset(("readme.md", "readme.txt", "skill.md", "notes.md", "changelog.md"))


def pick_source(case, materials):
    """The manuscript: what case.json names, else the longest prose that is not a README."""
    want = None
    if isinstance(case, dict):
        for k in ("material", "manuscript", "source", "source_file"):
            v = case.get(k)
            if isinstance(v, str) and v.lower().endswith((".md", ".txt", ".pdf", ".markdown")):
                want = v
                break
    prose = [m for m in materials if m["kind"] in ("text", "pdf") and m["text"].strip()
             and m["name"].lower() not in SKIP_PROSE]
    if want:
        for m in prose:
            if m["name"] == os.path.basename(want.replace("\\", "/")):
                return m
    if not prose:
        prose = [m for m in materials if m["kind"] == "json" and m["text"].strip()]
    return max(prose, key=lambda m: len(m["text"])) if prose else None


def run(case, materials, out_dir, draft_path=None, title=None):
    source = pick_source(case, materials)
    if source is None:
        empty = {"case_id": sk.case_id_of(case, []), "edited_text": "", "edits": [],
                 "checks": {"errors": [{"code": "no_material",
                                        "detail": "no readable manuscript"}],
                            "warnings": [], "summary": {}},
                 "metrics": {"edit_count": 0, "unexplained": 0, "number_drift": 0,
                             "hedge_drift": 0, "residual_grammar": 0}}
        return {"status": "failed", "main": empty,
                "errors": [{"code": "no_material", "detail": "no readable manuscript"}],
                "warnings": []}
    glossary = load_glossary(case, materials)
    src_sents = sentences_of(source["text"])
    plan = build_plan(source["name"], src_sents, glossary)
    sk.jdump(os.path.join(out_dir, "plan.json"), plan)

    draft = sk.load_draft(draft_path)
    edited_text, led_edits = draft_payload(draft)
    errors, warnings = [], []

    if not edited_text.strip():
        # No rewrite was submitted: say so, and do NOT write the source out as if it
        # were a polished manuscript.
        status = "partial"
        sk.jdump(os.path.join(out_dir, "edits.json"),
                 {"edits": [], "summary": {"edit_count": 0, "unexplained": 0}})
        sk.jdump(os.path.join(out_dir, "checks.json"),
                 {"errors": [], "warnings": [
                     {"code": "draft_missing", "detail": "no edited text in draft"}],
                  "sentences": [], "summary": {"n_errors": 0, "n_warnings": 1}})
        main = {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
                "edited_text": "", "edits": [],
                "checks": {"errors": [], "warnings": []},
                "metrics": {"edit_count": 0, "unexplained": 0, "number_drift": 0,
                            "hedge_drift": 0, "residual_grammar": 0},
                "files": {"plan": "plan.json", "checks": "checks.json",
                          "edits": "edits.json"}}
        return {"status": status, "main": main, "errors": [],
                "warnings": [{"code": "draft_missing"}],
                "sources": [m["path"] for m in materials]}

    ed_sents = sentences_of(edited_text)
    rows = align(src_sents, ed_sents)

    # ---------------- ledger validation ----------------
    ledger, seen_ids = [], set()
    for k, e in enumerate(led_edits, 1):
        eid = str(e.get("id") or "s%02d" % k)
        o = norm(e.get("original"))
        n = norm(e.get("edited"))
        typ = str(e.get("type") or "").strip().lower()
        reason = norm(e.get("reason") or "")
        row = {"id": eid, "original": o, "edited": n, "type": typ, "reason": reason,
               "source": "ledger", "anchored": bool(o) and (o in norm(source["text"])),
               "change_type": typ if typ in TYPES else "unchanged"}
        if eid in seen_ids:
            warnings.append({"code": "edit_duplicate_id", "id": eid,
                             "detail": "edit id used twice"})
        seen_ids.add(eid)
        if not row["anchored"]:
            errors.append({"code": "edit_unanchored", "id": eid,
                           "detail": "original text not found in the manuscript: %r" % o[:80]})
        if typ not in TYPES:
            errors.append({"code": "edit_bad_type", "id": eid,
                           "detail": "type must be one of grammar/term/tone/clarity, got %r" % typ})
        if not reason:
            errors.append({"code": "edit_unexplained", "id": eid,
                           "detail": "edit has no reason"})
        if o and n and o == n:
            warnings.append({"code": "edit_noop", "id": eid,
                             "detail": "original and edited are identical but a reason is given"})
        ledger.append(row)

    # ---------------- per-sentence checks ----------------
    sent_reports = []
    n_number_err = n_hedge_err = 0
    for r in rows:
        s_i, e_i = r["src"], r["ed"]
        s_txt = src_sents[s_i] if s_i is not None else ""
        e_txt = ed_sents[e_i] if e_i is not None else ""
        sid = "s%02d" % (s_i + 1) if s_i is not None else "ins%02d" % (e_i + 1)
        if s_i is not None and e_i is not None:
            ctype = classify(s_txt, e_txt, glossary)
            cov = _covering_row(ledger, s_txt, e_txt)
            if cov and cov["type"] in TYPES:
                ctype = cov["type"]     # the ledger's own label wins when valid
        else:
            ctype = "deleted" if e_i is None else "inserted"
        rep = {"id": sid, "op": r["op"], "change_type": ctype,
               "source": s_txt, "edited": e_txt, "issues": []}

        if r["op"] in ("delete", "insert"):
            warnings.append({"code": "alignment_gap", "id": sid,
                             "detail": ("source sentence has no counterpart (merged or removed)"
                                        if r["op"] == "delete" else
                                        "edited sentence has no source counterpart (added)")})
            rep["issues"].append("alignment_gap")
            sent_reports.append(rep)
            continue

        cs, ce = nums(s_txt), nums(e_txt)
        miss, extra = cs - ce, ce - cs
        if miss:
            n_number_err += 1
            errors.append({"code": "number_missing", "id": sid,
                           "detail": "numbers lost: " + ", ".join(sorted(miss)[:12])})
            rep["issues"].append("number_missing")
        if extra:
            n_number_err += 1
            errors.append({"code": "number_added", "id": sid,
                           "detail": "numbers not in the source: " + ", ".join(sorted(extra)[:12])})
            rep["issues"].append("number_added")
        if miss and extra and len(miss) == len(extra):
            n_number_err += 1
            pairs = ["%s -> %s" % (a, b) for a, b in zip(sorted(miss), sorted(extra))]
            errors.append({"code": "number_changed", "id": sid,
                           "detail": "number replaced: " + "; ".join(pairs[:8])})
            rep["issues"].append("number_changed")

        a_c, b_c = cite_set(s_txt), cite_set(e_txt)
        if a_c != b_c:
            errors.append({"code": "citation_changed", "id": sid,
                           "detail": "markers lost %s / added %s"
                                     % (sorted(a_c - b_c) or "-", sorted(b_c - a_c) or "-")})
            rep["issues"].append("citation_changed")

        if has_hedge(s_txt) and has_strong(e_txt) and not has_hedge(e_txt):
            n_hedge_err += 1
            errors.append({"code": "hedge_strengthened", "id": sid,
                           "detail": "hedged claim rewritten as a certainty"})
            rep["issues"].append("hedge_strengthened")
        elif has_strong(s_txt) and not has_hedge(s_txt) and has_hedge(e_txt) and not has_strong(e_txt):
            warnings.append({"code": "hedge_weakened", "id": sid,
                             "detail": "assertion softened; check that the claim still holds"})
            rep["issues"].append("hedge_weakened")

        if has_neg(s_txt) != has_neg(e_txt):
            errors.append({"code": "negation_changed", "id": sid,
                           "detail": "negation polarity flipped (%s -> %s)"
                                     % (has_neg(s_txt), has_neg(e_txt))})
            rep["issues"].append("negation_changed")

        for g in glossary:
            if not g["target"]:
                continue
            if g["source"] and g["source"].lower() in s_txt.lower():
                if g["target"].lower() not in e_txt.lower():
                    errors.append({"code": "term_missing", "id": sid,
                                   "detail": "locked form %r -> %r not used"
                                             % (g["source"], g["target"])})
                    rep["issues"].append("term_missing")
        sent_reports.append(rep)

    # ---------------- residual grammar lint ----------------
    lint = lint_grammar(edited_text)
    for it in lint:
        errors.append({"code": "residual_grammar", "rule": it["rule"],
                       "detail": it["detail"], "span": it["span"]})

    # ---------------- auto ledger for uncovered changes ----------------
    auto, unexplained_auto = [], 0
    pair_list = [r for r in rows if r["op"] == "replace"]
    for r in pair_list:
        s_txt, e_txt = src_sents[r["src"]], ed_sents[r["ed"]]
        sid = "s%02d" % (r["src"] + 1)
        if _covering_row(ledger, s_txt, e_txt):
            continue
        ctype = classify(s_txt, e_txt, glossary)
        auto.append({"id": sid, "original": norm(s_txt), "edited": norm(e_txt),
                     "type": ctype, "reason": "", "source": "auto",
                     "anchored": True, "change_type": ctype})
        unexplained_auto += 1

    for a in auto:
        errors.append({"code": "edit_unexplained", "id": a["id"],
                       "detail": "sentence changed but no ledger row with a reason "
                                 "(auto-generated from the diff)"})

    all_edits = ledger + auto
    # attach sentence ids to ledger rows when possible
    for e in ledger:
        for r in rows:
            if r["src"] is not None and e["original"] and e["original"] in norm(src_sents[r["src"]]):
                e["sentence"] = "s%02d" % (r["src"] + 1)
                break

    sk.jdump(os.path.join(out_dir, "edits.json"),
             {"edits": all_edits,
              "summary": {"edit_count": len(all_edits),
                          "ledger": len(ledger), "auto": len(auto),
                          "unexplained": sum(1 for e in errors if e["code"] == "edit_unexplained"),
                          "by_type": {t: sum(1 for e in all_edits if e["type"] == t)
                                      for t in TYPES}}})

    # ---------------- output artefacts ----------------
    md_lines = [edited_text.strip(), "", "---", "",
                "## 修改台账（与 edits.json 同源）", "",
                "| ID | 类型 | 原文 | 改后 | 理由 |", "|---|---|---|---|---|"]
    for e in all_edits:
        md_lines.append("| %s | %s | %s | %s | %s |" % (
            e["id"], e["type"] or "-",
            (e["original"] or "").replace("|", "\\|")[:160],
            (e["edited"] or "").replace("|", "\\|")[:160],
            (e["reason"] or "**缺少理由**").replace("|", "\\|")))
    with io.open(os.path.join(out_dir, "polished.md"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(md_lines) + "\n")

    metrics = {"edit_count": len(all_edits),
               "unexplained": sum(1 for e in errors if e["code"] == "edit_unexplained"),
               "number_drift": n_number_err,
               "hedge_drift": n_hedge_err,
               "residual_grammar": len(lint)}
    summary = {"n_sentences": len(src_sents), "n_edited_sentences": len(ed_sents),
               "n_errors": len(errors), "n_warnings": len(warnings)}
    sk.jdump(os.path.join(out_dir, "checks.json"),
             {"errors": errors, "warnings": warnings, "sentences": sent_reports,
              "summary": summary})

    status = "partial" if errors else "success"
    main = {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
            "edited_text": edited_text.strip(),
            "edits": all_edits,
            "checks": {"errors": errors, "warnings": warnings, "summary": summary,
                       "sentences": sent_reports},
            "metrics": metrics,
            "files": {"plan": "plan.json", "checks": "checks.json",
                      "edits": "edits.json", "polished": "polished.md"}}
    return {"status": status, "main": main, "errors": errors, "warnings": warnings,
            "sources": [m["path"] for m in materials]}
