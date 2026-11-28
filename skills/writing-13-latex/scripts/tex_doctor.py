# -*- coding: utf-8 -*-
"""tex_doctor -- deterministic LaTeX build doctor (stdlib only, offline).

The model writes or repairs the .tex; this module owns everything that must
not depend on a language model:

  * delimiter / environment / math-mode balance, each reported as file:line
    plus the original source line;
  * \\cite keys against the .bib (both directions);
  * \\ref keys against \\label keys and duplicate labels;
  * tabular column declarations against '&' counts, booktabs rules, captions;
  * high-confidence unescaped % & _ # in text mode;
  * duplicate \\usepackage;
  * two-pass pdflatex / latexmk when a TeX installation is present, with the
    log parsed into file:line diagnostics;
  * a deliberately small --fix: duplicate labels are renamed and \\ref
    synchronised, undefined citation keys become \\cite{TODO-key}.  Anything
    else is only described in the patch plan, never rewritten.

No network, no third-party imports, no rmtree.
"""
from __future__ import print_function

import os
import re
import shutil
import subprocess

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------
TABULAR_ENVS = ("tabular", "tabular*", "tabularx", "tabulary", "longtable", "array")
RULE_RE = re.compile(r"\\(toprule|midrule|bottomrule|hline|cmidrule|cline|addlinespace|specialrule)\b")
CITE_RE = re.compile(r"\\(cite[a-zA-Z]*|parencite|textcite|autocite|footcite|citealp)\*?"
                     r"(?:\[[^\]]*\])*\{([^}]*)\}")
REF_RE = re.compile(r"\\(ref|eqref|autoref|cref|Cref|pageref|nameref|subref)\*?\{([^}]*)\}")
LABEL_RE = re.compile(r"\\label\s*\{([^}]*)\}")
ENV_RE = re.compile(r"\\(begin|end)\s*\{([^}]*)\}")
PKG_RE = re.compile(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")
BIB_RE = re.compile(r"^\s*@([A-Za-z]+)\s*\{\s*([^,\s}]+)\s*,")

PROTECT_CMDS = frozenset((
    "label", "ref", "eqref", "autoref", "cref", "Cref", "pageref", "nameref",
    "subref", "cite", "citep", "citet", "citealp", "citeauthor", "citeyear",
    "citeyearpar", "parencite", "textcite", "autocite", "footcite",
    "includegraphics", "url", "href", "path", "input", "include",
    "includeonly", "bibliography", "bibliographystyle", "addbibresource",
    "begin", "end", "documentclass", "usepackage", "RequirePackage",
    "newcommand", "renewcommand", "providecommand", "DeclareMathOperator",
    "def", "verb", "bibitem", "graphicspath", "captionsetup",
))

PATCH_HINT = {
    "unbalanced_brace": "补齐或删掉多余的花括号；\\{ \\} 才是字面花括号。",
    "unbalanced_bracket": "补齐可选项的方括号；数学区间里的 [ 请放进数学模式。",
    "unbalanced_env": "让 \\begin{x} 与 \\end{x} 成对，注意嵌套顺序。",
    "unbalanced_math": "补上缺失的 $ 或改用 \\[ ... \\] / equation 环境。",
    "cite_undefined": "在 .bib 中补该条目，或改成已存在的 key。",
    "bib_unused": "在正文引用该条目，或从 .bib 删除。",
    "ref_undefined": "补一个 \\label{key}，或删掉悬空的 \\ref。",
    "label_duplicate": "把重复的 label 改成唯一名字并同步 \\ref。",
    "table_column_mismatch": "把列声明改成与实际列数一致，或在该行补/删 &。",
    "table_no_rules": "改用 booktabs 的 \\toprule / \\midrule / \\bottomrule。",
    "caption_missing": "在 table/figure 环境内加 \\caption{...}。",
    "unescaped_special": "在 % & _ # 前加反斜杠，或放进数学模式 / \\verb。",
    "package_duplicate": "删除重复的 \\usepackage 行。",
    "compile_error": "按 log 给出的 file:line 修 TeX 语法，再编译两遍。",
    "compiler_missing": "本机无 TeX；静态检查照跑，但不得声称编译成功。",
}


# --------------------------------------------------------------------------
# small text helpers
# --------------------------------------------------------------------------
def split_comment(raw):
    """Return (code, comment_index).  comment_index == -1 when no comment."""
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and i + 1 < len(raw):
            i += 2
            continue
        if ch == "%":
            return raw[:i], i
        i += 1
    return raw, -1


def match_group(s, i, open_ch="{", close_ch="}"):
    """Index of the closing delimiter matching s[i], or -1."""
    if i >= len(s) or s[i] != open_ch:
        return -1
    depth = 0
    j = i
    while j < len(s):
        ch = s[j]
        if ch == "\\":
            j += 2
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def norm_ws(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def reading_text(lines):
    return "\n".join(lines)


def diag(code, severity, file, line, text, detail, hint=None):
    return {"code": code, "severity": severity, "file": file, "line": line,
            "text": (text or "").rstrip(), "detail": detail,
            "hint": hint or PATCH_HINT.get(code, "")}


# --------------------------------------------------------------------------
# math mask + structural scans
# --------------------------------------------------------------------------
MATH_ENVS = ("equation", "equation*", "align", "align*", "eqnarray", "eqnarray*",
             "gather", "gather*", "multline", "multline*", "displaymath", "math")


def math_mask(code_lines):
    """Per-line bytearray, 1 where the character is inside math mode."""
    masks = [bytearray(len(c)) for c in code_lines]
    state = None  # None | "$" | "$$" | "[" | "("
    for i, c in enumerate(code_lines):
        j = 0
        while j < len(c):
            ch = c[j]
            if ch == "\\":
                two = c[j:j + 2]
                if state is None and two == "\\[":
                    state = "["
                    masks[i][j] = masks[i][j + 1] = 1
                    j += 2
                    continue
                if state is None and two == "\\(":
                    state = "("
                    masks[i][j] = masks[i][j + 1] = 1
                    j += 2
                    continue
                if state == "[" and two == "\\]":
                    state = None
                    masks[i][j] = masks[i][j + 1] = 1
                    j += 2
                    continue
                if state == "(" and two == "\\)":
                    state = None
                    masks[i][j] = masks[i][j + 1] = 1
                    j += 2
                    continue
                j += 2
                continue
            if ch == "$":
                if state is None:
                    if c[j:j + 2] == "$$":
                        state = "$$"
                        masks[i][j] = masks[i][j + 1] = 1
                        j += 2
                        continue
                    state = "$"
                    masks[i][j] = 1
                    j += 1
                    continue
                if state == "$":
                    state = None
                    masks[i][j] = 1
                    j += 1
                    continue
                if state == "$$" and c[j:j + 2] == "$$":
                    state = None
                    masks[i][j] = masks[i][j + 1] = 1
                    j += 2
                    continue
            if state is not None:
                masks[i][j] = 1
            j += 1
    # whole-line math environments
    env = None
    for i, c in enumerate(code_lines):
        stripped = c
        if env is None:
            m = re.search(r"\\begin\{(%s)\}" % "|".join(re.escape(e) for e in MATH_ENVS), stripped)
            if m:
                env = m.group(1)
                for k in range(m.end(), len(c)):
                    masks[i][k] = 1
        else:
            m = re.search(r"\\end\{%s\}" % re.escape(env), stripped)
            if m:
                for k in range(0, m.start()):
                    masks[i][k] = 1
                env = None
            else:
                for k in range(len(c)):
                    masks[i][k] = 1
    return masks


def scan_envs(code_lines, tex_name, lines):
    """Return (spans, errors).  spans: {name, start, end} line indexes."""
    stack, spans, errors = [], [], []
    for i, c in enumerate(code_lines):
        for m in ENV_RE.finditer(c):
            kind, name = m.group(1), m.group(2).strip()
            if kind == "begin":
                stack.append({"name": name, "line": i, "col": m.start()})
                continue
            if not stack:
                errors.append(diag("unbalanced_env", "error", tex_name, i + 1, lines[i],
                                   "\\end{%s} 没有对应的 \\begin" % name))
                continue
            if stack[-1]["name"] != name:
                errors.append(diag("unbalanced_env", "error", tex_name, i + 1, lines[i],
                                   "\\end{%s} 与第 %d 行的 \\begin{%s} 不匹配"
                                   % (name, stack[-1]["line"] + 1, stack[-1]["name"])))
                # try to recover: pop until a matching name, if any
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k]["name"] == name:
                        b = stack.pop(k)
                        spans.append({"name": name, "start": b["line"], "end": i,
                                      "begin_col": b["col"]})
                        del stack[k:]
                        break
                continue
            b = stack.pop()
            spans.append({"name": name, "start": b["line"], "end": i,
                          "begin_col": b["col"]})
    for b in stack:
        errors.append(diag("unbalanced_env", "error", tex_name, b["line"] + 1,
                           lines[b["line"]], "\\begin{%s} 到文件结尾都没有闭合" % b["name"]))
    return spans, errors


def check_braces(code_lines, tex_name, lines, chars="{", close="}", code_name="unbalanced_brace"):
    errors = []
    stack = []
    for i, c in enumerate(code_lines):
        j = 0
        while j < len(c):
            ch = c[j]
            if ch == "\\":
                j += 2
                continue
            if ch == chars:
                stack.append((i, j))
            elif ch == close:
                if stack:
                    stack.pop()
                else:
                    errors.append(diag(code_name, "error", tex_name, i + 1, lines[i],
                                       "多余的 '%s'，前面没有配对的 '%s'" % (close, chars)))
            j += 1
    for (i, j) in stack[:5]:
        errors.append(diag(code_name, "error", tex_name, i + 1, lines[i],
                           "未闭合的 '%s'（第 %d 列）" % (chars, j + 1)))
    return errors


def check_dollar(code_lines, tex_name, lines):
    errors = []
    total = 0
    last = 0
    for i, c in enumerate(code_lines):
        j = 0
        while j < len(c):
            if c[j] == "\\":
                j += 2
                continue
            if c[j] == "$":
                total += 1
                last = i
            j += 1
    if total % 2 == 1:
        errors.append(diag("unbalanced_math", "error", tex_name, last + 1, lines[last],
                           "$ 共 %d 个，奇数：数学模式没有闭合" % total))
    n_open = len(re.findall(r"\\\[", "\n".join(code_lines)))
    n_close = len(re.findall(r"\\\]", "\n".join(code_lines)))
    if n_open != n_close:
        errors.append(diag("unbalanced_math", "error", tex_name, last + 1, lines[last],
                           "\\[ 有 %d 个、\\] 有 %d 个，不配对" % (n_open, n_close)))
    return errors


# --------------------------------------------------------------------------
# protected spans (command arguments we must not call "prose")
# --------------------------------------------------------------------------
def protected_mask(code, masks_row):
    """Set of character indexes that belong to a command argument or verbatim."""
    out = set()
    i = 0
    while i < len(code):
        if masks_row[i]:
            out.add(i)
            i += 1
            continue
        if code[i] == "\\":
            m = re.match(r"\\([A-Za-z@]+)\*?", code[i:])
            if m:
                name = m.group(1)
                start = i
                i += len(m.group(0))
                if name in PROTECT_CMDS:
                    k = i
                    while k < len(code) and code[k] in " \t":
                        k += 1
                    while k < len(code) and code[k] == "[":
                        e = match_group(code, k, "[", "]")
                        if e < 0:
                            break
                        for x in range(start, e + 1):
                            out.add(x)
                        k = e + 1
                        while k < len(code) and code[k] in " \t":
                            k += 1
                    while k < len(code) and code[k] == "{":
                        e = match_group(code, k, "{", "}")
                        if e < 0:
                            break
                        for x in range(start, e + 1):
                            out.add(x)
                        k = e + 1
                    i = k
                    continue
                continue
            if code[i:i + 2] == "\\(" or code[i:i + 2] == "\\[":
                i += 2
                continue
            i += 2
            continue
        i += 1
    return out


def _inside_env(spans, name_set, line):
    for s in spans:
        if s["name"] in name_set and s["start"] <= line <= s["end"]:
            return True
    return False


def check_specials(code_lines, masks, spans, tex_name, lines):
    errors = []
    prog_lines = set()
    for s in spans:
        if s["name"] in TABULAR_ENVS or s["name"] in MATH_ENVS:
            prog_lines.update(range(s["start"], s["end"] + 1))
    for i, c in enumerate(code_lines):
        if not c.strip() or i in prog_lines:
            continue
        prot = protected_mask(c, masks[i])
        flags = []
        # '&' outside tabular / align
        k = 0
        while k < len(c):
            if c[k] == "\\":
                k += 2
                continue
            if c[k] == "&" and k not in prot:
                flags.append(("&", k))
                break
            k += 1
        # '_' between word characters in text mode
        for m in re.finditer(r"(?<=[A-Za-z0-9])_(?=[A-Za-z0-9])", c):
            if m.start() not in prot and not masks[i][m.start()]:
                flags.append(("_", m.start()))
                break
        # '#' outside macro definitions
        if not re.search(r"\\(newcommand|renewcommand|providecommand|def|newenvironment|DeclareMathOperator)\b", c):
            for m in re.finditer(r"(?<=[\sA-Za-z0-9])#(?=[A-Za-z0-9{])", c):
                if m.start() not in prot:
                    flags.append(("#", m.start()))
                    break
        # '%' that is most likely a lost literal percent
        _code, cidx = split_comment(lines[i])
        if cidx > 0:
            prev = lines[i][cidx - 1]
            rest = lines[i][cidx + 1:]
            words = re.findall(r"[A-Za-z]{2,}", rest)
            if prev.isdigit() and len(words) >= 2 and " " in rest.strip():
                flags.append(("%", cidx))
        if flags:
            ch, pos = flags[0]
            errors.append(diag("unescaped_special", "error", tex_name, i + 1, lines[i],
                               "正文里的 '%s' 未转义（第 %d 列）；%s"
                               % (ch, pos + 1, "疑为丢失的字面百分号" if ch == "%"
                                  else "应写成 \\%s 或放进数学/\\verb" % ch)))
    return errors


# --------------------------------------------------------------------------
# citations / refs / packages
# --------------------------------------------------------------------------
def parse_bib(bib_text, name):
    entries = []
    for i, line in enumerate(bib_text.split("\n")):
        m = BIB_RE.match(line)
        if not m:
            continue
        if m.group(1).lower() in ("string", "comment", "preamble"):
            continue
        entries.append({"key": m.group(2).strip(), "line": i + 1, "file": name,
                        "type": m.group(1)})
    return entries


def check_cites(code_lines, tex_name, lines, bib_entries):
    errors, warnings = [], []
    bib_keys = {e["key"] for e in bib_entries}
    used = []
    for i, c in enumerate(code_lines):
        for m in CITE_RE.finditer(c):
            for key in [x.strip() for x in m.group(2).split(",") if x.strip()]:
                used.append(key)
                if key.startswith("TODO-"):
                    continue
                if key not in bib_keys:
                    d = diag("cite_undefined", "error", tex_name, i + 1, lines[i],
                             "引用 key '%s' 不在 .bib 中" % key)
                    d["key"] = key
                    errors.append(d)
    uniq = []
    for k in used:
        if k not in uniq:
            uniq.append(k)
    for e in bib_entries:
        if e["key"] not in used:
            warnings.append(diag("bib_unused", "warning", e["file"], e["line"],
                                 "@%s{%s," % (e["type"], e["key"]),
                                 "该条目在正文中没有被引用"))
    todo = sorted({k for k in used if k.startswith("TODO-")})
    for k in todo:
        warnings.append(diag("cite_todo", "warning", tex_name, 1, "",
                             "占位引用 '%s' 需要人工补真实文献" % k))
    return errors, warnings, uniq


def check_refs(code_lines, tex_name, lines):
    errors, warnings = [], []
    labels = {}
    order = []
    for i, c in enumerate(code_lines):
        for m in LABEL_RE.finditer(c):
            key = m.group(1).strip()
            if key in labels:
                errors.append(diag("label_duplicate", "error", tex_name, i + 1, lines[i],
                                   "label '%s' 重复（首次在第 %d 行）"
                                   % (key, labels[key][0] + 1)))
            else:
                labels[key] = (i, m.start())
                order.append(key)
    for i, c in enumerate(code_lines):
        for m in REF_RE.finditer(c):
            key = m.group(2).strip()
            if key not in labels:
                errors.append(diag("ref_undefined", "error", tex_name, i + 1, lines[i],
                                   "\\%s{%s} 没有对应的 \\label" % (m.group(1), key)))
    return errors, warnings, labels, order


def check_packages(code_lines, tex_name, lines):
    warnings = []
    seen = {}
    for i, c in enumerate(code_lines):
        for m in PKG_RE.finditer(c):
            for name in [x.strip() for x in m.group(1).split(",") if x.strip()]:
                if name in seen:
                    warnings.append(diag("package_duplicate", "warning", tex_name, i + 1,
                                         lines[i], "宏包 '%s' 重复加载（首次第 %d 行）"
                                         % (name, seen[name] + 1)))
                else:
                    seen[name] = i
    return warnings


# --------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------
def parse_colspec(spec):
    cols = 0
    i = 0
    while i < len(spec):
        ch = spec[i]
        if ch in "pmb" and i + 1 < len(spec) and spec[i + 1] == "{":
            e = match_group(spec, i + 1, "{", "}")
            cols += 1
            i = (e + 1) if e > 0 else i + 2
            continue
        if ch in "lcrXSY":
            cols += 1
            i += 1
            continue
        if ch == "*" and i + 1 < len(spec) and spec[i + 1] == "{":
            e = match_group(spec, i + 1, "{", "}")
            if e < 0:
                i += 1
                continue
            try:
                times = int(spec[i + 2:e].strip())
            except ValueError:
                times = 1
            k = e + 1
            if k < len(spec) and spec[k] == "{":
                e2 = match_group(spec, k, "{", "}")
                if e2 > 0:
                    cols += times * parse_colspec(spec[k + 1:e2])
                    i = e2 + 1
                    continue
            i = e + 1
            continue
        if ch in "@!" and i + 1 < len(spec) and spec[i + 1] == "{":
            e = match_group(spec, i + 1, "{", "}")
            i = (e + 1) if e > 0 else i + 2
            continue
        i += 1
    return cols


def colspec_of(code_line, begin_col):
    """Column spec immediately after \\begin{tabular}[pos]{spec}."""
    i = begin_col
    m = re.match(r"\\begin\s*\{[^}]*\}", code_line[i:])
    if not m:
        return None
    i += m.end()
    while i < len(code_line) and code_line[i] in " \t":
        i += 1
    if i < len(code_line) and code_line[i] == "[":
        e = match_group(code_line, i, "[", "]")
        if e > 0:
            i = e + 1
    while i < len(code_line) and code_line[i] in " \t":
        i += 1
    if i < len(code_line) and code_line[i] == "{":
        e = match_group(code_line, i, "{", "}")
        if e > 0:
            return code_line[i + 1:e]
    return None


def _row_columns(code):
    amps = 0
    k = 0
    while k < len(code):
        if code[k] == "\\":
            k += 2
            continue
        if code[k] == "&":
            amps += 1
        k += 1
    extra = 0
    for m in re.finditer(r"\\multicolumn\s*\{(\d+)\}", code):
        try:
            extra += max(0, int(m.group(1)) - 1)
        except ValueError:
            pass
    return amps + 1 + extra


def check_tables(spans, code_lines, tex_name, lines):
    errors, warnings = [], []
    for s in spans:
        block = lines[s["start"]:s["end"] + 1]
        joined = "\n".join(block)
        name = s["name"]
        if name in TABULAR_ENVS:
            spec = colspec_of(code_lines[s["start"]], s["begin_col"])
            declared = parse_colspec(spec) if spec else None
            if declared:
                for i in range(s["start"] + 1, s["end"]):
                    code = code_lines[i]
                    if "&" not in code:
                        continue
                    if RULE_RE.search(code) and not code.strip().startswith("&"):
                        continue
                    got = _row_columns(code)
                    if got != declared:
                        errors.append(diag("table_column_mismatch", "error", tex_name, i + 1,
                                           lines[i],
                                           "列声明 {%s} 是 %d 列，该行有 %d 列"
                                           % (spec, declared, got)))
        if name in ("table", "table*"):
            if "\\caption" not in joined:
                warnings.append(diag("caption_missing", "warning", tex_name, s["start"] + 1,
                                     lines[s["start"]], "table 环境没有 \\caption"))
            if "\\begin{tabular" in joined and not RULE_RE.search(joined):
                warnings.append(diag("table_no_rules", "warning", tex_name, s["start"] + 1,
                                     lines[s["start"]], "表格没有 booktabs 三线或 \\hline"))
        if name in ("figure", "figure*"):
            if "\\caption" not in joined:
                warnings.append(diag("caption_missing", "warning", tex_name, s["start"] + 1,
                                     lines[s["start"]], "figure 环境没有 \\caption"))
    return errors, warnings


# --------------------------------------------------------------------------
# compile
# --------------------------------------------------------------------------
def find_engine():
    for exe in ("pdflatex", "latexmk"):
        path = shutil.which(exe)
        if path:
            return exe, path
    return None, None


def parse_log(text, default_file):
    out = []
    seen = set()
    rows = text.split("\n")
    for i, ln in enumerate(rows):
        m = re.match(r"^(?:\./)?([^:\\]{1,200}\.(?:tex|sty|cls)):(\d+):\s*(.*)$", ln)
        if m and "warning" not in m.group(3).lower():
            key = (m.group(2), norm_ws(m.group(3))[:120])
            if key in seen:
                continue
            seen.add(key)
            out.append({"file": os.path.basename(m.group(1)), "line": int(m.group(2)),
                        "message": norm_ws(m.group(3))})
            continue
        if ln.startswith("!"):
            msg = norm_ws(ln[1:])
            lineno = None
            for k in range(i + 1, min(i + 7, len(rows))):
                m2 = re.match(r"^l\.(\d+)\s", rows[k])
                if m2:
                    lineno = int(m2.group(1))
                    break
            key = (lineno, msg[:120])
            if key in seen:
                continue
            seen.add(key)
            out.append({"file": default_file, "line": lineno, "message": msg})
    return out[:20]


def compile_tex(tex_text, tex_name, bib_texts, work_dir, timeout=180):
    """Run a two-pass build when a TeX engine exists.

    Never claims success without a real build: with no engine the return value
    has compiled=False and compiler_missing=True.
    """
    engine, path = find_engine()
    if not engine:
        return {"available": False, "compiler_missing": True, "compiled": False,
                "engine": None, "errors": [], "log_tail": "",
                "note": "no pdflatex/latexmk on PATH; static checks only"}
    cdir = os.path.join(work_dir, "compile")
    if not os.path.isdir(cdir):
        os.makedirs(cdir)
    with open(os.path.join(cdir, tex_name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(tex_text)
    for bname, btext in (bib_texts or {}).items():
        with open(os.path.join(cdir, bname), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(btext)
    runs = []
    bibtex_missing = False
    version = ""
    try:
        vp = subprocess.run([path, "--version"], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=30)
        head = (vp.stdout or b"").decode("utf-8", "replace").splitlines()
        version = head[0].strip() if head else ""
    except Exception:
        version = ""
    if engine == "pdflatex":
        cmd = [path, "-interaction=nonstopmode", "-file-line-error",
               "-output-directory=" + cdir, tex_name]
        plan = [cmd]
        # a bibliography needs its own pass, otherwise \cite stays undefined
        # even though pdflatex exits 0
        bibtex = shutil.which("bibtex")
        if not bibtex:
            guess = os.path.join(os.path.dirname(path),
                                 "bibtex" + (".exe" if path.lower().endswith(".exe") else ""))
            bibtex = guess if os.path.exists(guess) else None
        if bibtex and bib_texts and re.search(
                r"\\(bibliography|addbibresource|printbibliography)", tex_text or ""):
            plan.append([bibtex, os.path.splitext(tex_name)[0]])
            plan += [cmd, cmd]
        else:
            # no bibtex on PATH: two passes only, and say so instead of pretending
            # the bibliography was resolved
            plan.append(cmd)
            if bib_texts and re.search(r"\\bibliography", tex_text or ""):
                bibtex_missing = True
    else:
        cmd = [path, "-pdf", "-interaction=nonstopmode", "-outdir=" + cdir, tex_name]
        plan = [cmd]
    for c in plan:
        try:
            p = subprocess.run(c, cwd=cdir, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=timeout)
            runs.append({"returncode": p.returncode,
                         "tail": (p.stdout or b"").decode("utf-8", "replace")[-400:]})
        except Exception as exc:  # timeout or missing binary
            runs.append({"returncode": -1, "tail": "%s: %s" % (type(exc).__name__, exc)})
    log_path = os.path.join(cdir, os.path.splitext(tex_name)[0] + ".log")
    log = ""
    if os.path.exists(log_path):
        with open(log_path, "rb") as fh:
            log = fh.read().decode("utf-8", "replace")
    errs = parse_log(log, tex_name)
    # bibtex reports to .blg, and its failures are also build failures
    blg = os.path.join(cdir, os.path.splitext(tex_name)[0] + ".blg")
    if os.path.exists(blg):
        with open(blg, "rb") as fh:
            blg_text = fh.read().decode("utf-8", "replace")
        for line in blg_text.splitlines():
            if line.lower().startswith(("i couldn't open", "error", "warning--")):
                errs.append({"file": os.path.basename(blg), "line": 0,
                             "message": line.strip()[:200]})
    pdf = os.path.join(cdir, os.path.splitext(tex_name)[0] + ".pdf")
    pdf_size = os.path.getsize(pdf) if os.path.exists(pdf) else 0
    ok = all(r["returncode"] == 0 for r in runs) and not errs and pdf_size > 0
    return {"available": True, "compiler_missing": False, "compiled": bool(ok),
            "engine": engine, "engine_version": version, "runs": len(runs),
            "bibtex_missing": bibtex_missing,
            "errors": errs, "pdf_path": pdf if pdf_size else None,
            "pdf_bytes": pdf_size,
            "log_tail": log[-1500:] if log else "",
            "note": "" if ok else "build failed or reported errors"}


# --------------------------------------------------------------------------
# --fix
# --------------------------------------------------------------------------
def apply_fixes(lines, tex_name, undef_cites):
    """Only two safe repairs; everything else is left to the patch plan."""
    fixes = []
    repl = {}  # line index -> list of (start, end, new_text)

    def add(i, a, b, text):
        repl.setdefault(i, []).append((a, b, text))

    # 1. duplicate labels -> key-2, key-3 ...
    seen = {}
    dups = []  # (line, key, newkey)
    for i, raw in enumerate(lines):
        code, _ = split_comment(raw)
        for m in LABEL_RE.finditer(code):
            key = m.group(1).strip()
            if key not in seen:
                seen[key] = i
                continue
            n = 2
            while ("%s-%d" % (key, n)) in seen:
                n += 1
            newkey = "%s-%d" % (key, n)
            seen[newkey] = i
            dups.append((i, key, newkey))
            add(i, m.start(1), m.end(1), newkey)
            fixes.append({"code": "label_duplicate", "file": tex_name, "line": i + 1,
                          "action": "rename \\label{%s} -> \\label{%s}" % (key, newkey),
                          "auto": True})

    # 1b. refs after the duplicate follow the renamed label
    ref_moves = 0
    for i, raw in enumerate(lines):
        code, _ = split_comment(raw)
        for m in REF_RE.finditer(code):
            key = m.group(2).strip()
            target = None
            for (dline, dkey, newkey) in dups:
                if dkey == key and dline <= i:
                    target = newkey
            if target:
                add(i, m.start(2), m.end(2), target)
                ref_moves += 1
    if ref_moves:
        fixes.append({"code": "ref_sync", "file": tex_name, "line": 0,
                      "action": "rewrite %d \\ref after a renamed label" % ref_moves,
                      "auto": True})

    # 2. undefined citation keys -> TODO-key
    todo = 0
    for i, raw in enumerate(lines):
        code, _ = split_comment(raw)
        for m in CITE_RE.finditer(code):
            keys = [x.strip() for x in m.group(2).split(",") if x.strip()]
            if not any(k in undef_cites for k in keys):
                continue
            new_keys = [("TODO-" + k if k in undef_cites else k) for k in keys]
            add(i, m.start(2), m.end(2), ",".join(new_keys))
            todo += 1
            fixes.append({"code": "cite_undefined", "file": tex_name, "line": i + 1,
                          "action": "placeholder \\cite{%s} -> \\cite{%s}"
                                    % (",".join(keys), ",".join(new_keys)),
                          "auto": True})

    out = list(lines)
    for i, items in repl.items():
        s = out[i]
        for (a, b, text) in sorted(items, key=lambda x: -x[0]):
            s = s[:a] + text + s[b:]
        out[i] = s
    return out, fixes


# --------------------------------------------------------------------------
# analysis entry
# --------------------------------------------------------------------------
def analyze(text, tex_name="main.tex", bib_texts=None):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    code_lines = [split_comment(x)[0] for x in lines]
    masks = math_mask(code_lines)
    spans, errors = scan_envs(code_lines, tex_name, lines)
    errors += check_braces(code_lines, tex_name, lines, "{", "}", "unbalanced_brace")
    errors += check_dollar(code_lines, tex_name, lines)
    errors += check_braces(code_lines, tex_name, lines, "[", "]", "unbalanced_bracket")
    errors += check_specials(code_lines, masks, spans, tex_name, lines)

    bib_entries = []
    for bname, btext in (bib_texts or {}).items():
        bib_entries += parse_bib(btext, bname)
    cite_err, cite_warn, cite_keys = check_cites(code_lines, tex_name, lines, bib_entries)
    ref_err, ref_warn, labels, label_order = check_refs(code_lines, tex_name, lines)
    tb_err, tb_warn = check_tables(spans, code_lines, tex_name, lines)
    pkg_warn = check_packages(code_lines, tex_name, lines)

    errors += cite_err + ref_err + tb_err
    warnings = cite_warn + ref_warn + tb_warn + pkg_warn
    # one unescaped-special per line is enough detail for a human to act on
    return {
        "errors": errors,
        "warnings": warnings,
        "stats": {"lines": len(lines), "cite_keys": cite_keys,
                  "labels": label_order, "n_labels": len(labels),
                  "bib_entries": [e["key"] for e in bib_entries],
                  "envs": len(spans)},
        "bib_entries": bib_entries,
        "lines": lines,
    }


def patch_plan(diags):
    out = []
    for d in diags:
        if d["code"] in ("cite_undefined", "label_duplicate"):
            continue  # handled by --fix
        out.append({"code": d["code"], "file": d["file"], "line": d["line"],
                    "target": d["text"][:160], "patch": d.get("hint") or PATCH_HINT.get(d["code"], "")})
    return out


def render_report(title, src_name, errors, warnings, fixes, patches, metrics, compile_info, pre):
    L = ["# LaTeX 编译体检：%s" % title, "",
         "- 主文件：`%s`" % src_name,
         "- status: **%s**" % ("success" if not errors else "partial"),
         "- errors: %d, warnings: %d" % (len(errors), len(warnings)),
         "- compiled: %s%s" % (metrics["compiled"],
                               " (compiler missing)" if compile_info.get("compiler_missing") else ""),
         ""]
    if pre:
        L += ["## 修复前", "", "- errors: %d, warnings: %d" % (pre["errors"], pre["warnings"]), ""]
    if fixes:
        L += ["## 已自动修复（--fix）", ""]
        for f in fixes:
            L.append("- `%s` %s:%s — %s" % (f["code"], f["file"], f["line"], f["action"]))
        L.append("")
    L += ["## 错误（必须改）", ""]
    if not errors:
        L.append("- 无")
    for e in errors:
        L.append("- `%s` **%s:%d** — %s" % (e["code"], e["file"], e["line"], e["detail"]))
        if e["text"]:
            L.append("  ```latex\n  %s\n  ```" % e["text"][:300])
    L += ["", "## 警告（需人工确认）", ""]
    if not warnings:
        L.append("- 无")
    for w in warnings:
        L.append("- `%s` **%s:%d** — %s" % (w["code"], w["file"], w["line"], w["detail"]))
        if w["text"]:
            L.append("  ```latex\n  %s\n  ```" % w["text"][:300])
    if compile_info.get("available") is False:
        L += ["", "## 编译", "", "- 本机没有 pdflatex/latexmk，**未编译**；"
              "`compiled=false`，不得声称编译成功。"]
    elif compile_info.get("errors"):
        L += ["", "## 编译日志", ""]
        for e in compile_info["errors"][:10]:
            L.append("- `%s:%s` %s" % (e["file"], e["line"], e["message"]))
    L += ["", "## 待人工修复清单（patch plan）", ""]
    if not patches:
        L.append("- 无")
    for p in patches[:40]:
        L.append("- `%s` %s:%s — %s" % (p["code"], p["file"], p["line"], p["patch"]))
    L.append("")
    return "\n".join(L)
