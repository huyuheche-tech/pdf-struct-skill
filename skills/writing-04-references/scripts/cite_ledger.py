# -*- coding: utf-8 -*-
"""cite_ledger -- deterministic reference / citation reconciliation.

The model decides what the citations mean; this module does what must not be
left to a language model:

  * parse a bibliography in three shapes (.bib, .ris, numbered text) and the
    in-text citations in four shapes ([1], [2,4], [3-5], \\cite{a,b},
    (Smith et al., 2020));
  * reconcile both directions: cited-but-absent, present-but-uncited,
    duplicated or gapped numbering;
  * renumber by first appearance and rewrite the manuscript (numeric markers
    only; \\cite keys and author-year forms are left alone);
  * de-duplicate: identical DOI, or normalised-title similarity >= 0.90 with
    the same first-author surname, with the basis recorded;
  * render GB/T 7714-2015 (or APA) with ``[TODO: field]`` for anything missing;
  * report per-entry completeness (author/title/year/source/doi) and type.

It never invents a field, a DOI or an entry.
"""
from __future__ import print_function

import io
import os
import re

import skillkit as sk

CJK = re.compile(r"[\u4e00-\u9fff]")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s,;}]+")

BIB_TYPE = {"article": "J", "inproceedings": "C", "conference": "C",
            "incollection": "C", "book": "M", "inbook": "M", "phdthesis": "D",
            "mastersthesis": "D", "thesis": "D", "misc": "EB", "online": "EB",
            "webpage": "EB", "electronic": "EB", "techreport": "EB",
            "unpublished": "EB"}
RIS_TYPE = {"JOUR": "J", "JFULL": "J", "CONF": "C", "CPAPER": "C", "BOOK": "M",
            "CHAP": "M", "THES": "D", "ELEC": "EB", "WEB": "EB", "GEN": "EB"}

REQ = {"J": ("volume", "pages"), "C": ("pages",), "M": (), "D": (), "EB": ()}
COMPLETENESS = ("author", "title", "year", "source", "doi")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def clean(s):
    s = (s or "").replace("\u00a0", " ")
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def strip_doi(s):
    s = (s or "").strip()
    s = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", s, flags=re.I)
    return s.strip().rstrip(".")


def split_authors(value):
    value = clean(value)
    if not value:
        return []
    parts = re.split(r"\s+and\s+", value, flags=re.I)
    if len(parts) == 1 and ";" in value:
        parts = value.split(";")
    out = []
    for p in parts:
        p = p.strip().strip(",")
        if p:
            out.append(p)
    return out


def _split_name(name):
    """(surname, given).  Understands 'Chen, Wei', 'Wei Chen' and 'Chen W'."""
    name = clean(name).strip()
    if not name:
        return "", ""
    if CJK.search(name):
        return name, ""
    if "," in name:
        last, given = name.split(",", 1)
        return last.strip(), given.strip()
    toks = name.split()
    if len(toks) == 1:
        return toks[0], ""
    if all(re.fullmatch(r"[A-Z]\.?", t) for t in toks[1:]):
        return toks[0], " ".join(toks[1:])        # GB/T form: Surname Initials
    return toks[-1], " ".join(toks[:-1])          # Given Surname


def surname(name):
    return _split_name(name)[0]


def first_surname(entry):
    return surname(entry["authors"][0]) if entry.get("authors") else ""


def is_cjk(s):
    return bool(CJK.search(s or ""))


# --------------------------------------------------------------------------
# BibTeX
# --------------------------------------------------------------------------
def _split_bib_fields(body):
    if "," in body:
        key, rest = body.split(",", 1)
    else:
        key, rest = body, ""
    fields, i, n = {}, 0, len(rest)
    while i < n:
        while i < n and rest[i] in " \t\r\n,":
            i += 1
        m = re.match(r"([A-Za-z][A-Za-z0-9_\-]*)\s*=\s*", rest[i:])
        if not m:
            break
        name = m.group(1).lower()
        i += m.end()
        if i < n and rest[i] == "{":
            depth, j, buf = 1, i + 1, []
            while j < n and depth:
                if rest[j] == "{":
                    depth += 1
                elif rest[j] == "}":
                    depth -= 1
                if depth:
                    buf.append(rest[j])
                j += 1
            val, i = "".join(buf), j
        elif i < n and rest[i] == '"':
            j = rest.find('"', i + 1)
            if j < 0:
                j = n
            val, i = rest[i + 1:j], j + 1
        else:
            m2 = re.match(r"[^,\s]+", rest[i:])
            if not m2:
                break
            val, i = m2.group(0), i + m2.end()
        fields[name] = clean(val)
    return key.strip(), fields


def parse_bib(text):
    entries = []
    for m in re.finditer(r"@([A-Za-z]+)\s*\{", text or ""):
        typ = m.group(1).lower()
        if typ in ("string", "comment", "preamble"):
            continue
        start, depth, j = m.end(), 1, m.end()
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        key, f = _split_bib_fields(text[start:j - 1])
        if not key:
            continue
        entries.append({"key": key, "raw_type": typ, "fields": f,
                        "type": BIB_TYPE.get(typ, "EB"), "fmt": "bib"})
    return entries


# --------------------------------------------------------------------------
# RIS
# --------------------------------------------------------------------------
def parse_ris(text):
    entries, cur, last = [], None, None
    for line in (text or "").splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])\s{2}-\s?(.*)$", line.rstrip())
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "TY":
            cur = {"ty": val, "au": [], "kw": []}
            last = "TY"
        elif cur is None:
            continue
        elif tag == "ER":
            entries.append(cur)
            cur = None
        elif tag == "AU":
            cur["au"].append(val)
            last = "AU"
        else:
            cur[tag] = val
            last = tag
    out = []
    for i, r in enumerate(entries, 1):
        f = {"author": " and ".join(r["au"]) if r.get("au") else "",
             "title": r.get("TI") or r.get("T1") or "",
             "year": (r.get("PY") or r.get("Y1") or "")[:4],
             "volume": r.get("VL") or "", "issue": r.get("IS") or "",
             "doi": r.get("DO") or "", "url": r.get("UR") or ""}
        pages = ""
        if r.get("SP"):
            pages = r["SP"] + ("-" + r["EP"] if r.get("EP") else "")
        f["pages"] = pages
        ty = RIS_TYPE.get((r.get("ty") or "").upper(), "EB")
        f["journal"] = r.get("JO") or r.get("JF") or r.get("T2") or ""
        f["booktitle"] = f["journal"]
        f["publisher"] = r.get("PB") or ""
        f["address"] = r.get("CY") or ""
        f["school"] = f["publisher"]
        out.append({"key": "ris%02d" % i, "raw_type": r.get("ty") or "",
                    "fields": f, "type": ty, "fmt": "ris"})
    return out


# --------------------------------------------------------------------------
# numbered text  ([1] Author. Title[J]. Journal, 2020, 12(3): 45-67.)
# --------------------------------------------------------------------------
NUM_LINE = re.compile(r"^\s*\[(\d+)\]\s*(.*)$")


def parse_numbered(text):
    blocks, cur = [], None
    for line in (text or "").splitlines():
        m = NUM_LINE.match(line)
        if m:
            if cur:
                blocks.append(cur)
            cur = [int(m.group(1)), m.group(2)]
        elif cur is not None and line.strip():
            cur[1] += " " + line.strip()
    if cur:
        blocks.append(cur)

    out = []
    for num, body in blocks:
        body = body.strip().rstrip(".")
        f = {}
        m = re.search(r"(?:DOI|doi)\s*[:：]\s*(\S+)\s*$", body)
        if m:
            f["doi"] = strip_doi(m.group(1))
            body = body[:m.start()].strip().rstrip(".")
        m = re.match(r"^(?P<a>.+?)[.。]\s*(?P<t>.+?)\s*\[(?P<y>[A-Z]{1,2})\]\s*[.。]?\s*(?P<r>.*)$",
                     body)
        if not m:
            out.append({"key": "n%02d" % num, "raw_type": "", "fmt": "txt",
                        "type": "EB", "number": num,
                        "fields": {"title": clean(body)}})
            continue
        f["author"] = re.sub(r"[,，;；]", " and ", m.group("a"))
        f["title"] = clean(m.group("t"))
        ty = m.group("y")[:1] if m.group("y")[0] in "JCMDEB" else "EB"
        if m.group("y").startswith("EB"):
            ty = "EB"
        rest = m.group("r").strip()
        parts = [p.strip() for p in re.split(r"[,，]", rest) if p.strip()]
        year = ""
        for p in parts:
            yy = re.fullmatch(r"(19|20)\d{2}", p)
            if yy:
                year = p
        f["year"] = year
        source = parts[0] if parts else ""
        vm = re.search(r"(\d+)\s*[（(]\s*([^)）]*?)\s*[)）]\s*[:：]\s*([0-9A-Za-z\-–]+)", rest)
        if vm:
            f["volume"], f["issue"], f["pages"] = vm.group(1), vm.group(2), vm.group(3)
            source = re.sub(r"\s*[,，]\s*$", "", rest[:vm.start()].strip(",， "))
            source = source.split(",")[0].strip() if "," in source else source
        else:
            pm = re.search(r"[:：]\s*(\d+\s*[-–]\s*\d+)", rest)
            if pm:
                f["pages"] = pm.group(1)
                source = rest[:pm.start()].strip(",， ")
        if ty == "M":
            f["publisher"] = source
            addr = re.match(r"^(.+?)\s*[:：]\s*(.+)$", source)
            if addr:
                f["address"], f["publisher"] = addr.group(1), addr.group(2)
        elif ty == "C":
            f["booktitle"] = source
        elif ty == "D":
            f["school"] = source
        else:
            f["journal"] = source
        out.append({"key": "n%02d" % num, "raw_type": m.group("y"), "fmt": "txt",
                    "type": ty, "number": num, "fields": f})
    return out


# --------------------------------------------------------------------------
# normalisation
# --------------------------------------------------------------------------
def normalise(raw, idx):
    f = raw["fields"]
    ty = raw["type"]
    journal = f.get("journal") or ""
    booktitle = f.get("booktitle") or f.get("journal") or ""
    publisher = f.get("publisher") or ""
    school = f.get("school") or f.get("publisher") or ""
    url = f.get("url") or ""
    if ty == "J":
        source = journal or booktitle
    elif ty == "C":
        source = booktitle or journal
    elif ty == "M":
        source = publisher
    elif ty == "D":
        source = school
    else:
        source = url or publisher or journal
    pages = (f.get("pages") or "").replace("--", "-").replace("–", "-")
    pages = re.sub(r"\s*-\s*", "-", pages)
    return {
        "id": "r%02d" % idx,
        "key": raw["key"],
        "number_old": raw.get("number", idx),
        "raw_type": raw.get("raw_type", ""),
        "type": ty,
        "fmt": raw.get("fmt", ""),
        "authors": split_authors(f.get("author")),
        "title": clean(f.get("title")),
        "year": (clean(f.get("year")) or "")[:4],
        "journal": journal, "booktitle": booktitle,
        "publisher": publisher, "address": f.get("address") or "",
        "school": school, "url": url,
        "source": source,
        "volume": clean(f.get("volume")),
        "issue": clean(f.get("issue") or f.get("number")),
        "pages": pages,
        "doi": strip_doi(f.get("doi")),
    }


def completeness(e):
    return {"author": bool(e["authors"]), "title": bool(e["title"]),
            "year": bool(re.fullmatch(r"(19|20)\d{2}", e["year"] or "")),
            "source": bool(e["source"]), "doi": bool(e["doi"])}


def label(e):
    return "%s (%s)" % (e["key"], e["year"] or "n.d.")


# --------------------------------------------------------------------------
# de-duplication
# --------------------------------------------------------------------------
def title_sim(a, b):
    return sk.similarity(a, b)


def merge_basis(a, b):
    """Return ('doi'|'title'|None, detail).  Only two safe bases exist."""
    if a["doi"] and b["doi"] and a["doi"].lower() == b["doi"].lower():
        return "doi", "identical DOI %s" % a["doi"]
    if first_surname(a) and first_surname(a).lower() == first_surname(b).lower():
        # "Part 1"/"Part 2", "GPT-3"/"GPT-4": a digit difference is a different paper,
        # no matter how similar the rest of the title is.
        na = re.findall(r"\d+", a["title"])
        nb = re.findall(r"\d+", b["title"])
        if na != nb:
            return None, "titles differ in their numbers (%s vs %s)" % (
                " ".join(na) or "-", " ".join(nb) or "-")
        ratio = title_sim(a["title"], b["title"])
        if ratio >= 0.90:
            return "title", "title similarity %.3f with the same first author %r" % (
                ratio, first_surname(a))
        return None, "same first author %r but title similarity %.3f < 0.90" % (
            first_surname(a), ratio)
    return None, "different first authors (%r vs %r)" % (
        first_surname(a) or "-", first_surname(b) or "-")


def _merge_fields(keep, drop):
    """Keep the more complete record, fill gaps from the other, union the rest."""
    for k in ("title", "year", "journal", "booktitle", "publisher", "address",
              "school", "source", "volume", "issue", "pages", "doi", "url"):
        if not keep.get(k) and drop.get(k):
            keep[k] = drop[k]
    if not keep["authors"] and drop["authors"]:
        keep["authors"] = drop["authors"]
    if drop["type"] == "J" and keep["type"] == "C":
        keep["type"] = "J"
    return keep


def dedupe(entries):
    """Return (groups, merges).  groups maps key -> representative key."""
    merges, groups = [], {e["key"]: e["key"] for e in entries}
    by_key = {e["key"]: e for e in entries}
    seen = set()
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            a, b = entries[i], entries[j]
            if (a["key"], b["key"]) in seen:
                continue
            basis, detail = merge_basis(a, b)
            if not basis:
                continue
            ka, kb = groups[a["key"]], groups[b["key"]]
            if ka == kb:
                continue
            keep, drop = by_key[ka], by_key[kb]
            if drop["type"] == "J" and keep["type"] == "C":
                keep, drop = drop, keep
            _merge_fields(keep, drop)
            for k, v in groups.items():
                if v == drop["key"]:
                    groups[k] = keep["key"]
            merges.append({"keys": sorted([a["key"], b["key"]]),
                           "kept": keep["key"], "dropped": drop["key"],
                           "basis": basis, "detail": detail})
            seen.add((a["key"], b["key"]))
    return groups, merges


# --------------------------------------------------------------------------
# citations
# --------------------------------------------------------------------------
AY_RE = re.compile(r"^\s*([A-Za-z\u4e00-\u9fff\-']+)(?:\s+et\s+al\.?)?\s*,\s*((?:19|20)\d{2})[a-z]?\s*$")


def parse_ay(raw):
    inner = raw.strip().strip("()（）")
    out = []
    for part in re.split(r"[;；]", inner):
        m = AY_RE.match(part.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def resolve(citations, by_number, by_key, entries):
    """[(citation, [entry key or None])] in document order."""
    out = []
    for c in citations:
        keys = []
        if c["style"] == "numeric":
            for i in c["ids"]:
                e = by_number.get(int(i)) if str(i).isdigit() else None
                keys.append(e["key"] if e else None)
        elif c["style"] == "latex":
            for k in c["ids"]:
                e = by_key.get(k.strip())
                keys.append(e["key"] if e else None)
        else:
            for n, y in parse_ay(c["raw"]):
                hit = None
                for e in entries:
                    if not e["authors"] or e["year"] != y:
                        continue
                    sur = first_surname(e)
                    full = clean(e["authors"][0])
                    if n.lower() in (sur.lower(), full.lower()) or \
                            full.lower().startswith(n.lower()):
                        hit = e["key"]
                        break
                keys.append(hit)
        out.append((c, keys))
    return out


def fmt_bracket(nums):
    nums = sorted(set(int(x) for x in nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            out.append("%d-%d" % (nums[i], nums[j]))
        else:
            out.extend(str(n) for n in nums[i:j + 1])
        i = j + 1
    return "[" + ",".join(out) + "]"


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def _fmt_author_gbt(name):
    name = clean(name)
    if not name:
        return ""
    if CJK.search(name):
        return name
    last, given = _split_name(name)
    initials = " ".join(p[0].upper() for p in re.split(r"[\s.\-]+", given) if p)
    return (last + (" " + initials if initials else "")).strip()


def _authors_gbt(authors):
    if not authors:
        return "[TODO: author]"
    names = [_fmt_author_gbt(a) for a in authors if clean(a)]
    if len(names) > 3:
        tail = "等" if any(CJK.search(n) for n in names) else "et al."
        return ", ".join(names[:3]) + ", " + tail
    return ", ".join(names)


def _todo(field):
    return "[TODO: %s]" % field


def render_gbt(e):
    """GB/T 7714-2015: 作者. 题名[类型]. 刊名, 年, 卷(期): 起页-止页. DOI: ..."""
    a = _authors_gbt(e["authors"])
    title = e["title"] or _todo("title")
    year = e["year"] if re.fullmatch(r"(19|20)\d{2}", e["year"] or "") else _todo("year")
    ty = e["type"]
    if ty == "J":
        src = e["journal"] or _todo("journal")
        vol = e["volume"] or _todo("volume")
        iss = e["issue"]
        pages = e["pages"] or _todo("pages")
        body = "%s. %s[J]. %s, %s, %s%s: %s." % (
            a, title, src, year, vol, "(%s)" % iss if iss else "", pages)
    elif ty == "C":
        src = e["booktitle"] or e["journal"] or _todo("booktitle")
        pages = e["pages"] or _todo("pages")
        body = "%s. %s[C]//%s. %s: %s." % (a, title, src, year, pages)
    elif ty == "M":
        src = e["publisher"] or _todo("publisher")
        if e["address"]:
            src = "%s: %s" % (e["address"], src)
        body = "%s. %s[M]. %s, %s." % (a, title, src, year)
    elif ty == "D":
        src = e["school"] or _todo("school")
        body = "%s. %s[D]. %s, %s." % (a, title, src, year)
    else:
        src = e["url"] or e["publisher"] or _todo("url")
        body = "%s. %s[EB/OL]. %s, %s." % (a, title, src, year)
    if e["doi"]:
        body += " DOI: %s." % e["doi"]
    else:
        body += " " + _todo("doi") + "."
    return re.sub(r"\.\.+", ".", body).strip()


def _fmt_author_apa(name):
    name = clean(name)
    if not name:
        return ""
    if CJK.search(name):
        return name
    last, given = _split_name(name)
    initials = " ".join(p[0].upper() + "." for p in re.split(r"[\s.\-]+", given) if p)
    return "%s, %s" % (last, initials) if initials else last


def render_apa(e):
    names = [_fmt_author_apa(a) for a in e["authors"] if clean(a)]
    if not names:
        a = _todo("author")
    elif len(names) == 1:
        a = names[0]
    else:
        a = ", ".join(names[:-1]) + ", & " + names[-1]
    year = e["year"] or _todo("year")
    vol = e["volume"]
    src = e["source"] or _todo("source")
    loc = ", ".join([x for x in (vol, "(%s)" % e["issue"] if e["issue"] else "",
                                 e["pages"]) if x])
    body = "%s (%s). %s. %s%s." % (a, year, e["title"] or _todo("title"),
                                   src, (", " + loc) if loc else "")
    if e["doi"]:
        body += " https://doi.org/%s" % e["doi"]
    return re.sub(r"\.\.+", ".", body).strip()


def render(entry, style):
    return render_apa(entry) if (style or "").lower() == "apa" else render_gbt(entry)


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------
SKIP_PROSE = frozenset(("readme.md", "readme.txt", "skill.md", "notes.md", "changelog.md"))


def split_materials(case, materials):
    """(manuscript, libraries).  Names in case.json win; README-like files never win."""
    want_man, want_lib = None, []
    if isinstance(case, dict):
        for k in ("manuscript", "material", "source"):
            v = case.get(k)
            if isinstance(v, str) and v.lower().endswith((".md", ".txt", ".pdf", ".markdown", ".tex")):
                want_man = os.path.basename(v.replace("\\", "/"))
                break
        lib = case.get("library") or case.get("bibliography") or case.get("library_file")
        if isinstance(lib, str):
            want_lib = [os.path.basename(lib.replace("\\", "/"))]
        elif isinstance(lib, list):
            want_lib = [os.path.basename(str(x).replace("\\", "/")) for x in lib]

    manuscript, libs = None, []
    for m in materials:
        if m["kind"] in ("bib", "ris"):
            libs.append(m)
            continue
        txt = m["text"] if m["text"].strip() else ""
        if txt and re.match(r"^\s*\[\d+\]\s+\S", txt.strip().splitlines()[0]):
            libs.append(m)
            continue
        if m["kind"] in ("text", "pdf", "tex") and txt:
            if m["name"].lower() in SKIP_PROSE:
                continue
            if manuscript is None or len(txt) > len(manuscript["text"]):
                manuscript = m

    if want_lib:
        picked = [m for m in libs if m["name"] in want_lib]
        if picked:
            libs = picked
    if want_man:
        hit = [m for m in materials if m["name"] == want_man and m["text"].strip()]
        if hit:
            manuscript = hit[0]
    return manuscript, libs


def _empty_failure(case, materials, code, detail):
    main = {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
            "references": [], "renumber_map": {},
            "bibliography": "", "manuscript_renumbered": "",
            "checks": {"errors": [{"code": code, "detail": detail}], "warnings": []},
            "metrics": {"entries": 0, "cited": 0, "uncited": 0, "missing": 0,
                        "duplicates": 0, "field_completeness": None}}
    return {"status": "failed", "main": main,
            "errors": [{"code": code, "detail": detail}], "warnings": [],
            "sources": [m["path"] for m in materials]}



STOPWORDS = set("""the a an of and or to in on for with by is are was were be as at from
that this these those we our it its their using use used based results method methods paper
study studies show shows shown can may might also more than between among under over""".split())


def _content_tokens(text):
    t = (text or "").lower()
    words = [w for w in re.findall(r"[a-z][a-z0-9\-]{2,}", t) if w not in STOPWORDS]
    cjk = re.findall(r"[\u4e00-\u9fff]{2,}", t)
    grams = []
    for chunk in cjk:
        grams.extend(chunk[i:i + 2] for i in range(max(1, len(chunk) - 1)))
    return set(words) | set(grams)


def _sentence_around(text, a, b):
    left = max(text.rfind(ch, 0, a) for ch in ".!?\n\u3002\uff01\uff1f") + 1
    rights = [text.find(ch, b) for ch in ".!?\n\u3002\uff01\uff1f"]
    rights = [x for x in rights if x >= 0]
    right = (min(rights) + 1) if rights else len(text)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def citation_contexts(text, resolved, by_key):
    """For every in-text citation: the sentence it supports and the cited title.

    A zero-overlap flag is a *hint* for a human ("this citation may not support
    this sentence"), not proof: titles and claims often share no surface words.
    """
    out, warnings = [], []
    for c, keys in resolved:
        sent = _sentence_around(text, c["span"][0], c["span"][1])
        for k in keys:
            e = by_key.get(k) if k else None
            if not e:
                continue
            title = e.get("title") or ""
            ts, ss = _content_tokens(title), _content_tokens(sent)
            overlap = len(ts & ss) if ts else None
            row = {"citation": c["raw"], "key": k, "sentence": sent[:300],
                   "title": title[:200], "overlap": overlap,
                   "position": ("paragraph_end" if sent and
                                text.rfind("\n", 0, c["span"][0]) >= 0 and
                                len(sent) > 180 else "sentence")}
            out.append(row)
            if overlap == 0 and len(ts) >= 3:
                warnings.append({"code": "claim_topic_mismatch", "key": k,
                                 "detail": "no content word shared between the citing sentence "
                                           "and the cited title; check that the citation supports "
                                           "this claim"})
    return out, warnings


def run(case, materials, out_dir, draft_path=None, style="gbt7714", check_only=False):
    manuscript, libs = split_materials(case, materials)
    if not manuscript:
        return _empty_failure(case, materials, "no_manuscript", "no readable manuscript")
    if not libs:
        return _empty_failure(case, materials, "no_library",
                              "no .bib / .ris / numbered bibliography found")

    raw = []
    for m in libs:
        if m["kind"] == "bib":
            raw.extend(parse_bib(m["text"]))
        elif m["kind"] == "ris":
            raw.extend(parse_ris(m["text"]))
        else:
            raw.extend(parse_numbered(m["text"]))
    entries = [normalise(r, i) for i, r in enumerate(raw, 1)]
    fmt = libs[0]["kind"] if len(libs) == 1 else "mixed"

    errors, warnings = [], []

    # 1. numbering sanity (only meaningful for a numbered list)
    numbers = [e["number_old"] for e in entries]
    if fmt == "text" or any(e["fmt"] == "txt" for e in entries):
        seen = set()
        for n in numbers:
            if n in seen:
                warnings.append({"code": "number_gap", "detail": "number [%d] used twice" % n})
            seen.add(n)
        top = max(numbers) if numbers else 0
        for k in range(1, top + 1):
            if k not in seen:
                warnings.append({"code": "number_gap",
                                 "detail": "number [%d] missing from the list" % k})

    # 2. de-duplication
    groups, merges = dedupe(entries)
    kept = {e["key"]: e for e in entries if groups[e["key"]] == e["key"]}
    for mg in merges:
        warnings.append({"code": "duplicate_entry",
                         "detail": "merged %s into %s (%s)" % (
                             " + ".join(mg["keys"]), mg["kept"], mg["detail"])})

    # 3. draft: proposed merges + completeness claims
    _draft = sk.load_draft(draft_path)
    has_draft = isinstance(_draft, dict) and bool(draft_path)
    draft = _draft if isinstance(_draft, dict) else {}
    by_key = {e["key"]: e for e in entries}
    for pair in (draft.get("merges") or []):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            warnings.append({"code": "draft_bad_merge", "detail": "merge proposal is not a pair"})
            continue
        ka, kb = str(pair[0]), str(pair[1])
        if ka not in by_key or kb not in by_key:
            errors.append({"code": "unknown_key",
                           "detail": "merge proposal cites an unknown key: %s" % pair})
            continue
        if groups[ka] == groups[kb]:
            continue                                  # already merged by the engine
        basis, detail = merge_basis(by_key[ka], by_key[kb])
        if basis:
            keep, drop = by_key[ka], by_key[kb]
            if drop["type"] == "J" and keep["type"] == "C":
                keep, drop = drop, keep
            _merge_fields(keep, drop)
            for k, v in groups.items():
                if v == drop["key"]:
                    groups[k] = keep["key"]
            merges.append({"keys": sorted([ka, kb]), "kept": keep["key"],
                           "dropped": drop["key"], "basis": basis, "detail": detail,
                           "proposed_by": "draft"})
            warnings.append({"code": "duplicate_entry",
                             "detail": "merged %s + %s (%s)" % (ka, kb, detail)})
        else:
            errors.append({"code": "unsafe_merge",
                           "detail": "refused merge of %s and %s: %s" % (ka, kb, detail)})
    kept = {e["key"]: e for e in entries if groups[e["key"]] == e["key"]}

    # 4. citations
    by_number = {e["number_old"]: e for e in entries}
    cites = sk.citations(manuscript["text"])
    resolved = resolve(cites, by_number, by_key, entries)
    order, missing, seen_missing = [], [], set()
    cited_keys = set()
    for c, keys in resolved:
        for k in keys:
            if k is None:
                if c["raw"] not in seen_missing:
                    seen_missing.add(c["raw"])
                    rec = {"code": "missing_entry",
                           "detail": "cited but not in the bibliography: %r" % c["raw"]}
                    missing.append(rec)
                    errors.append(rec)
                continue
            g = groups[k]
            cited_keys.add(g)
            if g not in order:
                order.append(g)

    # uncited entries keep their place at the end so nothing silently disappears
    tail = [e["key"] for e in entries if groups[e["key"]] == e["key"]
            and groups[e["key"]] not in order]
    order.extend(tail)
    for k in tail:
        warnings.append({"code": "uncited_entry",
                         "detail": "%s is in the bibliography but never cited" % k})

    contexts, ctx_warnings = citation_contexts(manuscript["text"], resolved, kept)
    warnings.extend(ctx_warnings)

    new_no = {k: i for i, k in enumerate(order, 1)}

    # 5. completeness claims
    declared = set(str(x) for x in (draft.get("declared_complete") or []))
    for e in entries:
        if groups[e["key"]] != e["key"]:
            continue
        comp = completeness(e)
        for f in COMPLETENESS:
            if comp[f]:
                continue
            rec = {"code": "field_missing",
                   "detail": "%s has no %s%s" % (
                       e["key"], f,
                       "; the draft claims this entry is complete" if e["key"] in declared else ""),
                   "key": e["key"], "field": f}
            if e["key"] in declared:
                rec["severity"] = "error"   # do not let a claim outrun the record
                errors.append(rec)
            else:
                rec["severity"] = "warning"  # rendered as [TODO: field]
                warnings.append(rec)
        for f in REQ.get(e["type"], ()):
            if not e.get(f):
                rec = {"code": "field_missing",
                       "detail": "%s has no %s (required for type %s)"
                                 % (e["key"], f, e["type"]),
                       "key": e["key"], "field": f, "severity": "warning"}
                if not any(w["code"] == "field_missing" and w["key"] == e["key"]
                           and w["field"] == f for w in warnings):
                    warnings.append(rec)

    # 6. rewrite numeric markers
    text = manuscript["text"]
    reps = []
    if not check_only:
        for c, keys in resolved:
            if c["style"] != "numeric":
                continue
            nums = []
            for k in keys:
                if k is None or groups[k] not in new_no:
                    nums = None
                    break
                nums.append(new_no[groups[k]])
            if not nums:
                continue
            repl = fmt_bracket(nums)
            if repl != c["raw"]:
                reps.append((c["span"][0], c["span"][1], repl))
        for a, b, r in sorted(reps, reverse=True):
            text = text[:a] + r + text[b:]

    renumber_map = []
    for e in entries:
        g = groups[e["key"]]
        renumber_map.append({"old": e["number_old"], "key": e["key"],
                             "new": new_no.get(g), "merged_into": None if g == e["key"] else g,
                             "cited": g in cited_keys})

    # 7. bibliography
    bib_lines = []
    style_label = "APA 7" if (style or "").lower() == "apa" else "GB/T 7714-2015"
    for k in order:
        e = kept[k]
        bib_lines.append("[%d] %s" % (new_no[k], render(e, style)))
    bibliography = "# 参考文献（%s）\n\n%s\n" % (style_label, "\n\n".join(bib_lines))

    refs = []
    for e in entries:
        if groups[e["key"]] != e["key"]:
            continue
        comp = completeness(e)
        refs.append({
            "id": e["id"], "key": e["key"], "type": e["type"],
            "number_old": e["number_old"], "number_new": new_no.get(e["key"]),
            "authors": e["authors"], "title": e["title"], "year": e["year"],
            "source": e["source"], "volume": e["volume"], "issue": e["issue"],
            "pages": e["pages"], "doi": e["doi"],
            "cited": e["key"] in cited_keys,
            "cite_count": sum(1 for c, keys in resolved
                              for k in keys if k and groups[k] == e["key"]),
            "completeness": comp,
            "complete": all(comp.values()),
            "todo": [f for f in COMPLETENESS if not comp[f]],
            "merged_from": sorted(k for k in groups if groups[k] == e["key"] and k != e["key"]),
            "gbt7714": render_gbt(e),
            "apa": render_apa(e),
        })

    n_cited = sum(1 for r in refs if r["cited"])
    metrics = {"entries": len(refs), "parsed_entries": len(entries),
               "cited": n_cited, "uncited": len(refs) - n_cited,
               "missing": len(missing), "duplicates": len(merges),
               "field_completeness": (round(
                   sum(1 for r in refs if r["complete"]) / float(max(1, len(refs))), 3))}

    summary = {"n_errors": len(errors), "n_warnings": len(warnings),
               "n_citations": len(cites), "style": style or "gbt7714"}
    checks = {"errors": errors, "warnings": warnings, "summary": summary,
              "citations": [{"raw": c["raw"], "style": c["style"],
                             "keys": [groups[k] if k else None for k in keys]}
                            for c, keys in resolved]}

    with io.open(os.path.join(out_dir, "bibliography.md"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write(bibliography)
    if not check_only:
        with io.open(os.path.join(out_dir, "manuscript_renumbered.md"), "w",
                     encoding="utf-8", newline="\n") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
    sk.jdump(os.path.join(out_dir, "checks.json"), checks)
    sk.jdump(os.path.join(out_dir, "references.json"),
             {"entries": refs, "renumber_map": renumber_map, "merges": merges,
              "issues": {"errors": errors, "warnings": warnings},
              "style": style or "gbt7714", "format": fmt})

    if not has_draft:
        status = "partial"      # mechanics done, editorial claims (merges/completeness) not
    elif errors:
        status = "partial"
    else:
        status = "success"

    main = {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
            "references": refs,
            "renumber_map": renumber_map,
            "checks": checks,
            "bibliography": bibliography,
            "manuscript_renumbered": "" if check_only else text.strip(),
            "citation_contexts": contexts,
            "merges": merges,
            "metrics": dict(metrics, citation_contexts=len(contexts),
                            topic_mismatch=sum(1 for w in warnings
                                               if w.get("code") == "claim_topic_mismatch")),
            "files": {"references": "references.json", "checks": "checks.json",
                      "bibliography": "bibliography.md",
                      "manuscript_renumbered": None if check_only
                      else "manuscript_renumbered.md"}}
    return {"status": status, "main": main, "errors": errors, "warnings": warnings,
            "sources": [m["path"] for m in materials], "draft": has_draft}
