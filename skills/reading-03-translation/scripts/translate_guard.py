# -*- coding: utf-8 -*-
"""translate_guard -- deterministic guard for a bilingual translation case.

The model does the language work; this module does everything that must not be
left to a language model:

  * stable paragraph / sentence IDs (so nothing can be silently dropped);
  * a locked glossary (so a term cannot drift between title, body and caption);
  * number / unit / citation / formula preservation checks;
  * negation and hedge polarity checks (so a claim is not strengthened);
  * optional back-translation similarity;
  * a bilingual markdown table that can be checked line by line.

It never translates by itself.  Without a draft it emits a plan and says so.
"""
from __future__ import print_function

import os
import re

import skillkit as sk

NEG_EN = r"\b(?:not|no|never|none|neither|nor|cannot|can't|doesn't|don't|isn't|aren't|wasn't|weren't|without|fail(?:s|ed)? to|unable)\b"
NEG_ZH = r"(?:不|未|无|非|没有|无法|不能|并未|尚未|缺乏|否定)"
HEDGE_EN = r"\b(?:may|might|could|would|suggest(?:s|ed)?|indicat(?:e|es|ed)|appear(?:s|ed)?|likely|possibly|probably|approximately|about|roughly|tend(?:s|ed)? to|seems?)\b"
HEDGE_ZH = r"(?:可能|或许|也许|大概|约|近似|似乎|提示|表明|倾向于|有望)"
FORMULA_RE = re.compile(r"\$\$?[^$]{1,400}\$\$?|\\\(.{1,300}?\\\)|\\\[.{1,300}?\\\]|\\begin\{(equation|align|eqnarray)\*?\}.{0,2000}?\\end\{\1\*?\}", re.S)


def _strip_spans(text, spans):
    out, last = [], 0
    for a, b in sorted(spans):
        out.append(text[last:a])
        last = max(last, b)
    out.append(text[last:])
    return "".join(out)


def _cjk_target(lang):
    return (lang or "").lower().startswith(("zh", "ja", "ko", "chinese")) or "中文" in (lang or "")


def load_glossary(case, materials):
    """Accept [{source,target,note}], {src:tgt}, or a CSV/TSV material."""
    items = []
    raw = None
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
                if "source" in head or "term" in head or "原文" in head:
                    si = 0
                    ti = 1 if len(head) > 1 else 1
                    for h in ("target", "translation", "译名", "译文"):
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
    # de-duplicate on normalised source, keep the first non-empty target
    seen = {}
    for it in items:
        k = sk.norm_key(it["source"])
        if not k:
            continue
        if k not in seen or (not seen[k]["target"] and it["target"]):
            seen[k] = {"source": it["source"].strip(), "target": (it["target"] or "").strip(),
                       "note": (it.get("note") or "").strip()}
    return sorted(seen.values(), key=lambda x: -len(x["source"]))


def zone_of(index, total, text):
    """Coarse role label used only for the glossary consistency matrix."""
    t = (text or "").strip()
    if index == 0 and len(t) < 200:
        return "title"
    if re.match(r"^(abstract|摘要)\b", t, re.I):
        return "abstract"
    if re.search(r"\b(Figure|Fig\.|Table)\s*\d+", t) or t.lower().startswith(("图", "表")):
        return "caption"
    if re.match(r"^(references|参考文献)\b", t, re.I) or re.match(r"^\[\d+\]", t):
        return "reference"
    return "body"


def build_plan(source_name, segs, glossary, target_lang):
    zones = {}
    plan = []
    for i, s in enumerate(segs):
        z = zone_of(i, len(segs), s["text"])
        zones.setdefault(z, 0)
        zones[z] += 1
        hits = []
        for g in glossary:
            if g["source"] and re.search(re.escape(g["source"]), s["text"], re.I):
                hits.append({"source": g["source"], "target": g["target"]})
        plan.append({
            "id": s["id"],
            "zone": z,
            "source": s["text"],
            "sentences": s["sentences"],
            "locked_terms": hits,
            "numbers": [n["raw"] for n in sk.numbers(s["text"])],
            "citations": [c["raw"] for c in sk.citations(s["text"])],
            "formulas": FORMULA_RE.findall(s["text"]) if FORMULA_RE.search(s["text"]) else [],
            "target_hint": ("translate into %s; keep every number, citation marker and formula verbatim"
                            % (target_lang or "the target language")),
        })
    return {
        "source": source_name,
        "target_language": target_lang,
        "n_segments": len(segs),
        "zones": zones,
        "glossary_size": len(glossary),
        "glossary": glossary,
        "segments": plan,
        "instruction": ("Write draft.json as {\"segments\":[{\"id\":\"p001\",\"target\":\"...\"}]}. "
                        "Every id must appear exactly once. Do not merge or split paragraph ids. "
                        "Use the locked target for every glossary term. Keep numbers, citation "
                        "markers and formulas byte-for-byte."),
    }


def _draft_map(draft):
    if not draft:
        return {}, []
    if isinstance(draft, dict) and isinstance(draft.get("segments"), list):
        rows = draft["segments"]
        return ({str(r.get("id")): (r.get("target") or r.get("text") or "") for r in rows
                 if isinstance(r, dict) and r.get("id")}, rows)
    if isinstance(draft, dict) and isinstance(draft.get("translations"), dict):
        return {str(k): str(v) for k, v in draft["translations"].items()}, []
    if isinstance(draft, dict):
        flat = {k: v for k, v in draft.items() if isinstance(v, str)}
        if flat:
            return flat, []
    return {}, []


def validate(segs, plan_by_id, draft_map, glossary, target_lang, back=None):
    errors, warnings = [], []
    cjk = _cjk_target(target_lang)
    row_reports = []
    seen = set()
    for s in segs:
        sid = s["id"]
        target = (draft_map.get(sid) or "").strip()
        rep = {"id": sid, "zone": plan_by_id[sid]["zone"], "ok": True,
               "issues": [], "n_source_chars": len(s["text"]), "n_target_chars": len(target)}
        if sid in seen:
            errors.append({"code": "duplicate_segment", "id": sid,
                           "detail": "id appears more than once in draft"})
        seen.add(sid)
        if not target:
            errors.append({"code": "missing_segment", "id": sid,
                           "detail": "no target text for this paragraph"})
            rep["ok"] = False
            rep["issues"].append("missing")
            row_reports.append(rep)
            continue

        # 1. numbers and units
        src_nums = sk.number_multiset(_strip_spans(s["text"], [c["span"] for c in sk.citations(s["text"])]))
        tgt_nums = sk.number_multiset(_strip_spans(target, [c["span"] for c in sk.citations(target)]))
        missing_nums = sorted((src_nums - tgt_nums).elements())
        extra_nums = sorted((tgt_nums - src_nums).elements())
        if missing_nums:
            errors.append({"code": "number_missing", "id": sid,
                           "detail": "numbers absent from target: " + ", ".join(missing_nums[:12])})
            rep["ok"] = False; rep["issues"].append("number_missing")
        if extra_nums:
            warnings.append({"code": "number_added", "id": sid,
                             "detail": "numbers not in source: " + ", ".join(extra_nums[:12])})

        # 2. citations
        src_cites = [c["raw"] for c in sk.citations(s["text"])]
        for raw in src_cites:
            if sk.one_line(raw) not in sk.one_line(target):
                # author-year may legitimately become "等"; accept the year+first author
                inner = re.sub(r"[()\[\]]", "", raw)
                first = re.split(r"[,;]", inner)[0].strip()
                if first and first.split()[0] in target:
                    warnings.append({"code": "citation_localised", "id": sid,
                                     "detail": "citation %r rendered differently" % raw})
                else:
                    errors.append({"code": "citation_missing", "id": sid,
                                   "detail": "citation marker %r not found in target" % raw})
                    rep["ok"] = False; rep["issues"].append("citation_missing")

        # 3. formulas (regex has one capturing group; use finditer for full text)
        for m in FORMULA_RE.finditer(s["text"]):
            raw = m.group(0)
            if raw not in target:
                errors.append({"code": "formula_changed", "id": sid,
                               "detail": "formula/env not preserved: %r" % raw[:60]})
                rep["ok"] = False; rep["issues"].append("formula_changed")

        # 4. glossary enforcement
        for g in glossary:
            if not g["target"]:
                continue
            if re.search(re.escape(g["source"]), s["text"], re.I):
                if cjk:
                    hit = g["target"] in target
                else:
                    hit = re.search(r"\b" + re.escape(g["target"]) + r"(?:s|es|ed|ing)?\b", target, re.I) is not None
                if not hit:
                    errors.append({"code": "term_missing", "id": sid,
                                   "detail": "locked term %r -> %r not used" % (g["source"], g["target"])})
                    rep["ok"] = False; rep["issues"].append("term_missing")

        # 5. negation / hedge polarity
        src_neg = bool(re.search(NEG_EN, s["text"], re.I) or re.search(NEG_ZH, s["text"]))
        tgt_neg = bool(re.search(NEG_EN, target, re.I) or re.search(NEG_ZH, target))
        if src_neg and not tgt_neg:
            errors.append({"code": "negation_lost", "id": sid,
                           "detail": "source negates, target has no negation cue"})
            rep["ok"] = False; rep["issues"].append("negation_lost")
        if not src_neg and tgt_neg:
            warnings.append({"code": "negation_added", "id": sid,
                             "detail": "target adds a negation cue"})
        src_hedge = bool(re.search(HEDGE_EN, s["text"], re.I) or re.search(HEDGE_ZH, s["text"]))
        tgt_hedge = bool(re.search(HEDGE_EN, target, re.I) or re.search(HEDGE_ZH, target))
        if src_hedge and not tgt_hedge:
            warnings.append({"code": "hedge_lost", "id": sid,
                             "detail": "source hedges, target reads as a stronger claim"})

        # 6. length sanity
        ratio = len(target) / max(1, len(s["text"]))
        rep["ratio"] = round(ratio, 2)
        if ratio < 0.25 or ratio > 3.0:
            warnings.append({"code": "length_outlier", "id": sid,
                             "detail": "target/source character ratio %.2f" % ratio})

        # 7. optional back-translation
        if back and isinstance(back, dict) and sid in back:
            sim = sk.similarity(s["text"], back[sid])
            rep["back_similarity"] = round(sim, 3)
            if sim < 0.45:
                warnings.append({"code": "back_translation_diverges", "id": sid,
                                 "detail": "similarity %.2f; check for omissions" % sim})
        row_reports.append(rep)

    unknown = sorted(set(draft_map) - set(plan_by_id))
    for uid in unknown:
        warnings.append({"code": "unknown_segment", "id": uid,
                         "detail": "draft contains an id that is not in the source"})
    return errors, warnings, row_reports


def glossary_matrix(segs, plan_by_id, draft_map, glossary, target_lang):
    cjk = _cjk_target(target_lang)
    rows = []
    for g in glossary:
        cells = {}
        for s in segs:
            if not g["target"]:
                continue
            if not re.search(re.escape(g["source"]), s["text"], re.I):
                continue
            z = plan_by_id[s["id"]]["zone"]
            tgt = draft_map.get(s["id"], "")
            ok = (g["target"] in tgt) if cjk else bool(re.search(r"\b" + re.escape(g["target"]) + r"(?:s|es|ed|ing)?\b", tgt, re.I))
            cells.setdefault(z, {"used": 0, "ok": 0})
            cells[z]["used"] += 1
            cells[z]["ok"] += 1 if ok else 0
        if cells:
            rows.append({"source": g["source"], "target": g["target"],
                         "zones": {z: "%d/%d" % (v["ok"], v["used"]) for z, v in cells.items()},
                         "consistent": all(v["ok"] == v["used"] for v in cells.values())})
    return rows


def render_markdown(title, segs, plan_by_id, draft_map, report):
    lines = ["# 双语对照：%s" % title, "",
             "| 段号 | 位置 | 原文 | 译文 | 校验 |", "|---|---|---|---|---|"]
    for s in segs:
        tgt = (draft_map.get(s["id"]) or "").replace("|", "\\|").replace("\n", " ")
        src = s["text"].replace("|", "\\|").replace("\n", " ")
        rep = report.get(s["id"], {})
        flag = "OK" if rep.get("ok") else ",".join(rep.get("issues") or ["missing"])
        lines.append("| %s | %s | %s | %s | %s |" % (s["id"], plan_by_id[s["id"]]["zone"],
                                                      src, tgt, flag))
    return "\n".join(lines) + "\n"


def run(case, materials, out_dir, draft_path=None, target_lang=None, title=None):
    prose = [m for m in materials if m["kind"] in ("text", "pdf") and m["text"].strip()]
    if not prose:
        prose = [m for m in materials if m["kind"] == "json" and m["text"].strip()]
    if not prose:
        return {"status": "failed", "main": {}, "errors": [{"code": "no_material"}],
                "warnings": []}
    source = max(prose, key=lambda m: len(m["text"]))
    text = source["text"]
    paras = [p for p in sk.split_paragraphs(text) if len(p) > 1]
    segs = sk.segments(paras)
    glossary = load_glossary(case, materials)
    lang = target_lang or (case.get("target_language") if isinstance(case, dict) else None) or "zh"
    plan = build_plan(source["name"], segs, glossary, lang)
    sk.jdump(os.path.join(out_dir, "plan.json"), plan)

    draft = sk.load_draft(draft_path)
    draft_map, _rows = _draft_map(draft)
    back = draft.get("back_translation") if isinstance(draft, dict) else None
    plan_by_id = {p["id"]: p for p in plan["segments"]}
    errors, warnings, row_reports = validate(segs, plan_by_id, draft_map, glossary, lang, back)
    report = {r["id"]: r for r in row_reports}

    matrix = glossary_matrix(segs, plan_by_id, draft_map, glossary, lang) if draft_map else []
    translated = sum(1 for s in segs if (draft_map.get(s["id"]) or "").strip())
    hard = len(errors)
    if not draft_map:
        status = "partial"
    elif hard:
        status = "partial"
    else:
        status = "success"

    md = render_markdown(title or source["name"], segs, plan_by_id, draft_map, report)
    with open(os.path.join(out_dir, "translation.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)
    sk.jdump(os.path.join(out_dir, "checks.json"),
             {"errors": errors, "warnings": warnings, "segments": row_reports,
              "glossary_matrix": matrix,
              "summary": {"n_segments": len(segs), "translated": translated,
                          "n_errors": len(errors), "n_warnings": len(warnings)}})

    main = {
        "case_id": sk.case_id_of(case, [m["path"] for m in materials]),
        "translation": md,
        "segments": [{"id": s["id"], "zone": plan_by_id[s["id"]]["zone"],
                      "source": s["text"], "target": draft_map.get(s["id"], ""),
                      "ok": report.get(s["id"], {}).get("ok", False)}
                     for s in segs],
        "glossary": matrix or glossary,
        "checks": {"errors": errors, "warnings": warnings,
                   "summary": {"n_segments": len(segs), "translated": translated,
                               "n_errors": len(errors), "n_warnings": len(warnings)}},
        "metrics": {"segment_coverage": round(translated / max(1, len(segs)), 3),
                    "term_consistency": (round(sum(1 for r in matrix if r["consistent"]) /
                                               max(1, len(matrix)), 3) if matrix else None),
                    "number_fidelity": (1.0 if not any(e["code"] == "number_missing" for e in errors)
                                        else None)},
        "files": {"plan": "plan.json", "checks": "checks.json", "translation": "translation.md"},
    }
    unc = {"warnings": warnings,
           "human_review": [w for w in warnings if w["code"] in
                            ("hedge_lost", "number_added", "citation_localised",
                             "back_translation_diverges", "length_outlier")],
           "missing_fields": [],
           "note": ("numbers/citations/formulas are checked byte-for-byte; terminology is "
                    "checked against the locked glossary; anything not checked is listed "
                    "as a warning rather than silently passed")}
    return {"status": status, "main": main, "errors": errors, "warnings": warnings,
            "plan": plan, "sources": [m["path"] for m in materials]}
