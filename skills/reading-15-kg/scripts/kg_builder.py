# -*- coding: utf-8 -*-
"""kg_builder -- deterministic literature knowledge-graph builder (stdlib only).

Two independent papers go in, one evidence-linked graph comes out.  The model
proposes nodes, edges and queries; this module owns the part that must not be
delegated to a language model:

  * paragraph lookup by JATS paragraph_id (never PDF page numbers);
  * byte-level evidence resolution (every edge quote must exist in the cited
    paragraph of the cited paper);
  * controlled relation vocabulary, direction, dangling and self-loop checks;
  * merge policy: same name + same type must be one node with a merge_basis;
    same name + different type must stay two nodes and be logged as a conflict;
    a cross-paper merge must cite both papers;
  * cross-paper overreach: two papers' numbers may not be fused into one
    comparative edge without conditions;
  * queries are executed for real and must carry node/edge ids plus evidence;
  * incremental mode keeps existing ids and reports added / merged / conflicting.

It never invents a graph: without a draft it emits candidate entities marked
candidate=true and says so.
"""
from __future__ import print_function

import csv
import io
import os
import re

import skillkit as sk

NODE_TYPES = ("method", "dataset", "metric", "finding", "material", "task", "author")
RELATIONS = ("uses", "compares", "outperforms", "supports", "contradicts",
             "part_of", "measured_by")
COMPARATIVE = ("outperforms", "compares")


# --------------------------------------------------------------------------
# corpus loading
# --------------------------------------------------------------------------
def load_corpus(materials):
    """Return {papers, order, manifest, index, docs} from json/md/txt inputs."""
    docs = {}
    for m in materials:
        if m.get("kind") == "json":
            try:
                obj = sk.jload(m["path"])
            except Exception:
                continue
            docs[os.path.basename(m["path"])] = obj
    manifest = None
    for name, obj in docs.items():
        if "manifest" in name.lower() and isinstance(obj, dict):
            manifest = obj
            break
    index = None
    for name, obj in docs.items():
        if name.lower() == "material.json" and isinstance(obj, dict):
            index = obj
            break
    if index is None:
        for name, obj in docs.items():
            if isinstance(obj, dict) and isinstance(obj.get("papers"), list) \
                    and obj["papers"] and all(isinstance(p, dict) and p.get("file")
                                              for p in obj["papers"]):
                index = obj
                break

    file_to_pid = {}
    order = []
    if index:
        for p in index.get("papers", []):
            if isinstance(p, dict) and p.get("paper_id"):
                file_to_pid[os.path.basename(p.get("file") or "")] = p["paper_id"]
                order.append(p["paper_id"])
    if manifest:
        for p in manifest.get("papers", []):
            if isinstance(p, dict) and p.get("paper_id") and p["paper_id"] not in order:
                order.append(p["paper_id"])

    papers = {}
    for name, obj in docs.items():
        if not isinstance(obj, dict) or not isinstance(obj.get("paragraphs"), list):
            continue
        pid = obj.get("paper_id") or file_to_pid.get(name)
        if not pid:
            pid = "p%d" % (len(papers) + 1)
        paras = {}
        for i, para in enumerate(obj["paragraphs"], 1):
            if not isinstance(para, dict):
                continue
            text = para.get("text") or para.get("content") or ""
            ppid = para.get("paragraph_id") or ("%s-%d" % (pid, i))
            paras[ppid] = {"text": text, "section": para.get("section") or ""}
        papers[pid] = {"paper_id": pid, "title": obj.get("title") or "",
                       "doi": obj.get("doi") or "", "file": name,
                       "paragraphs": paras}
        if pid not in order:
            order.append(pid)

    # text fallback: md/txt become numbered paragraphs of their own paper
    for m in materials:
        if m.get("kind") not in ("text",) or not m.get("text", "").strip():
            continue
        pid = "p%d" % (len(papers) + 1)
        paras = {}
        for i, para in enumerate([x for x in sk.split_paragraphs(m["text"]) if len(x) > 1], 1):
            paras["%s-%d" % (pid, i)] = {"text": para, "section": ""}
        if paras:
            papers[pid] = {"paper_id": pid, "title": os.path.basename(m["path"]),
                           "doi": "", "file": m["name"], "paragraphs": paras}
            order.append(pid)

    meta = {}
    if manifest:
        for p in manifest.get("papers", []):
            if isinstance(p, dict) and p.get("paper_id"):
                meta[p["paper_id"]] = {
                    "doi": p.get("doi") or "",
                    "license": p.get("license") or "",
                    "source_hash": p.get("source_hash") or "",
                    "title": p.get("title") or "",
                    "authors": p.get("authors") or [],
                    "role": p.get("role") or "",
                }
    return {"papers": papers, "order": [p for p in order if p in papers],
            "manifest": manifest, "index": index, "meta": meta, "docs": docs}


# --------------------------------------------------------------------------
# graph helpers
# --------------------------------------------------------------------------
def name_keys(node):
    keys = set()
    for s in [node.get("name")] + list(node.get("aliases") or []):
        k = sk.norm_key(s)
        if k:
            keys.add(k)
    return keys


def node_papers(node):
    out = []
    for pid in node.get("source_ids") or []:
        if pid not in out:
            out.append(pid)
    for ev in node.get("evidence") or []:
        pid = ev.get("source_id")
        if pid and pid not in out:
            out.append(pid)
    return out


def resolve(pid, para_id, quote, papers):
    paper = papers.get(pid)
    if not paper:
        return False, "unknown paper %r" % (pid,)
    para = paper["paragraphs"].get(para_id or "")
    if not para:
        return False, "unknown paragraph_id %r in %s" % (para_id, pid)
    ok, _, _ = sk.check_quote(quote, para["text"])
    if not ok:
        return False, "quote not found in %s/%s" % (pid, para_id)
    return True, ""


def _pair(a, b):
    return tuple(sorted((a, b)))


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------
def check_edges(edges, nodes_by_id, papers):
    errors = []
    resolved = {}
    for e in edges:
        eid = e.get("id") or "?"
        for field in ("source_id", "paragraph_id", "quote"):
            if not e.get(field):
                errors.append({"code": "evidence_unresolved", "id": eid,
                               "detail": "edge %s is missing %s" % (eid, field)})
        if e.get("source_id") and e.get("paragraph_id") and e.get("quote"):
            ok, why = resolve(e["source_id"], e["paragraph_id"], e["quote"], papers)
            resolved[eid] = ok
            if not ok:
                errors.append({"code": "evidence_unresolved", "id": eid,
                               "detail": "edge %s: %s" % (eid, why),
                               "source_id": e["source_id"],
                               "paragraph_id": e["paragraph_id"]})
        else:
            resolved[eid] = False
        rel = e.get("relation")
        if rel not in RELATIONS:
            errors.append({"code": "relation_invalid", "id": eid,
                           "detail": "relation %r not in %s" % (rel, ",".join(RELATIONS))})
        for side in ("source", "target"):
            nid = e.get(side)
            if nid not in nodes_by_id:
                errors.append({"code": "dangling_edge", "id": eid,
                               "detail": "edge %s %s=%r is not a node" % (eid, side, nid)})
        if e.get("source") and e.get("source") == e.get("target"):
            errors.append({"code": "self_loop", "id": eid,
                           "detail": "edge %s links %s to itself" % (eid, e["source"])})
    return errors, resolved


def check_node_evidence(nodes, papers):
    errors, warnings = [], []
    for n in nodes:
        nid = n.get("id") or "?"
        evs = n.get("evidence") or []
        if not n.get("source_ids") and not evs:
            errors.append({"code": "evidence_unresolved", "id": nid,
                           "detail": "node %s has no source_ids" % nid})
            continue
        for ev in evs:
            ok, why = resolve(ev.get("source_id"), ev.get("paragraph_id"),
                              ev.get("quote"), papers)
            if not ok:
                errors.append({"code": "evidence_unresolved", "id": nid,
                               "detail": "node %s evidence: %s" % (nid, why)})
        if not evs and not n.get("candidate"):
            warnings.append({"code": "node_unevidenced", "id": nid,
                             "detail": "node %s has source_ids but no paragraph quote" % nid})
    return errors, warnings


def check_merges(nodes, skip_pairs=None):
    """Cluster by shared name/alias; enforce the merge policy."""
    errors, warnings, conflicts = [], [], []
    skip_pairs = skip_pairs or set()
    parent = {n["id"]: n["id"] for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    key_owner = {}
    for n in nodes:
        for k in name_keys(n):
            if k in key_owner:
                union(key_owner[k], n["id"])
            else:
                key_owner[k] = n["id"]

    clusters = {}
    for n in nodes:
        clusters.setdefault(find(n["id"]), []).append(n)

    for group in clusters.values():
        types = {n.get("type") for n in group}
        ids = [n["id"] for n in group]
        if len(group) > 1 and len(types) > 1:
            attempted = [n for n in group if n.get("merge_basis") or n.get("merged_from")]
            name = group[0].get("name")
            detail = ("name %r appears with types %s; keep them as separate nodes"
                      % (name, "/".join(sorted(t or "?" for t in types))))
            conflicts.append({"ids": ids, "name": name, "types": sorted(t or "" for t in types),
                              "reason": "name_conflict"})
            if attempted:
                errors.append({"code": "name_conflict", "id": ",".join(ids),
                               "detail": detail + " (a merge was attempted)"})
            else:
                warnings.append({"code": "name_conflict", "id": ",".join(ids),
                                 "detail": detail})
        elif len(group) > 1 and len(types) == 1:
            reason = "same name and type but %d ids" % len(group)
            conflicts.append({"ids": ids, "name": group[0].get("name"),
                              "types": [group[0].get("type")], "reason": "unmerged_duplicate"})
            if _pair(ids[0], ids[1]) in skip_pairs:
                warnings.append({"code": "unmerged_duplicate", "id": ",".join(ids),
                                 "detail": reason + " (kept, recorded as an incremental conflict)"})
            else:
                errors.append({"code": "unmerged_duplicate", "id": ",".join(ids),
                               "detail": reason + "; merge them and give a merge_basis"})

    by_id = {n["id"]: n for n in nodes}
    for n in nodes:
        src = set(n.get("source_ids") or [])
        merged_from = n.get("merged_from") or []
        if merged_from:
            missing = [x for x in merged_from if x not in by_id]
            if missing:
                errors.append({"code": "merge_unsourced", "id": n["id"],
                               "detail": "merged_from references unknown ids: " + ",".join(missing)})
                continue
            papers = set()
            for x in merged_from:
                papers |= set(node_papers(by_id[x]))
            if len(papers) >= 2 and not src.issuperset(papers):
                errors.append({"code": "merge_unsourced", "id": n["id"],
                               "detail": "cross-paper merge must list all source papers %s"
                                         % ",".join(sorted(papers))})
        if not merged_from and len(src) >= 2 and not (n.get("merge_basis") or "").strip():
            errors.append({"code": "merge_unsourced", "id": n["id"],
                           "detail": "node %s spans %d papers but has no merge_basis"
                                     % (n["id"], len(src))})
    return errors, warnings, conflicts


def check_overreach(edges, nodes_by_id, resolved):
    errors = []
    for e in edges:
        eid = e.get("id") or "?"
        src = nodes_by_id.get(e.get("source"))
        tgt = nodes_by_id.get(e.get("target"))
        if not src or not tgt:
            continue
        papers = set(node_papers(src)) | set(node_papers(tgt))
        if len(papers) < 2:
            continue
        cond = (e.get("conditions") or "").strip()
        if cond:
            continue
        rel = e.get("relation")
        if not (rel in COMPARATIVE or e.get("cross_paper")):
            continue
        if not resolved.get(eid):
            continue
        errors.append({"code": "cross_paper_overreach", "id": eid,
                       "detail": ("edge %s fuses %s into '%s' without conditions; "
                                  "the quote comes from only one paper"
                                  % (eid, "/".join(sorted(papers)), rel))})
    return errors


def run_queries(queries, nodes, edges, resolved):
    out = []
    by_id = {n["id"]: n for n in nodes}
    edge_by_id = {e.get("id"): e for e in edges}
    for i, q in enumerate(queries):
        qid = q.get("id") or "q%d" % (i + 1)
        text = q.get("q") or q.get("query") or ""
        declared = [a for a in (q.get("answer_ids") or []) if a]
        evidence, dangling = [], []
        for aid in declared:
            if aid in edge_by_id:
                e = edge_by_id[aid]
                if resolved.get(aid):
                    evidence.append({"kind": "edge", "id": aid,
                                     "source_id": e.get("source_id"),
                                     "paragraph_id": e.get("paragraph_id"),
                                     "quote": e.get("quote")})
                continue
            if aid not in by_id:
                dangling.append(aid)
                continue
            hits = 0
            for e in edges:
                if aid in (e.get("source"), e.get("target")) and resolved.get(e.get("id")):
                    evidence.append({"kind": "edge", "id": e.get("id"), "node": aid,
                                     "source_id": e.get("source_id"),
                                     "paragraph_id": e.get("paragraph_id"),
                                     "quote": e.get("quote")})
                    hits += 1
                    if hits >= 2:
                        break
        matched = []
        qn = sk.norm_key(text)
        for n in nodes:
            for k in name_keys(n):
                if k and len(k) > 3 and k in qn:
                    matched.append(n["id"])
                    break
        out.append({"id": qid, "q": text, "declared": declared,
                    "matched_nodes": matched, "evidence": evidence[:4],
                    "dangling": dangling,
                    "empty_reason": q.get("empty_reason") or "",
                    "executed": True})
    return out


def check_queries(queries, executed):
    errors = []
    if len(queries) < 3:
        errors.append({"code": "queries_thin", "id": "queries",
                       "detail": "only %d queries; at least 3 are required" % len(queries)})
    for q in executed:
        if q["dangling"] and not q["evidence"] and not q["empty_reason"]:
            errors.append({"code": "query_unevidenced", "id": q["id"],
                           "detail": "answer ids not in graph: " + ",".join(q["dangling"])})
            continue
        if not q["declared"] and not q["empty_reason"]:
            errors.append({"code": "query_unevidenced", "id": q["id"],
                           "detail": "query returns no ids and gives no empty_reason"})
        elif q["declared"] and not q["evidence"]:
            errors.append({"code": "query_unevidenced", "id": q["id"],
                           "detail": "answers %s carry no resolvable evidence"
                                     % ",".join(q["declared"][:4])})
    return errors


def check_orphans(nodes, edges):
    linked = set()
    for e in edges:
        linked.add(e.get("source"))
        linked.add(e.get("target"))
    warnings = []
    for n in nodes:
        if n.get("candidate"):
            continue
        if n.get("id") not in linked:
            warnings.append({"code": "orphan_node", "id": n["id"],
                             "detail": "node %s (%s) has no edge" % (n["id"], n.get("name"))})
    return warnings


# --------------------------------------------------------------------------
# candidate extraction (no draft)
# --------------------------------------------------------------------------
STOP_TERMS = frozenset((
    "the", "this", "that", "these", "those", "we", "our", "all", "only", "each",
    "both", "their", "there", "here", "which", "what", "when", "with", "from",
    "and", "but", "for", "not", "are", "was", "were", "has", "have", "had",
    "one", "two", "also", "same", "such", "than", "then", "they", "its",
))


def candidates(corpus):
    out = []
    i = 0
    for pid in corpus["order"]:
        paper = corpus["papers"][pid]
        for ppid, para in paper["paragraphs"].items():
            for c in sk.term_candidates(para["text"], min_count=1)[:4]:
                name = c["term"]
                if len(name) < 3 or name.lower().strip() in STOP_TERMS:
                    continue
                i += 1
                sent = sk.split_sentences(para["text"])
                quote = next((s for s in sent if name in s), para["text"][:120])
                out.append({"id": "c%d" % i, "name": name, "type": None,
                            "candidate": True, "aliases": [], "merge_basis": "",
                            "source_ids": [pid],
                            "evidence": [{"source_id": pid, "paragraph_id": ppid,
                                          "quote": quote[:200]}]})
                if len(out) >= 24:
                    return out
    return out


# --------------------------------------------------------------------------
# incremental merge
# --------------------------------------------------------------------------
def merge_incremental(base, nodes, edges):
    added_nodes, added_edges, merged, conflicting = [], [], [], []
    base_nodes = {}
    for n in base.get("nodes") or []:
        nn = dict(n)
        base_nodes[nn["id"]] = nn
    key_owner = {}
    for n in base_nodes.values():
        for k in name_keys(n):
            key_owner.setdefault((k, n.get("type")), n["id"])
    out_nodes = list(base_nodes.values())
    remap = {}
    skip_pairs = set()

    for n in nodes:
        nid = n["id"]
        if nid in base_nodes:
            b = base_nodes[nid]
            if sk.norm_key(b.get("name")) == sk.norm_key(n.get("name")) \
                    and b.get("type") == n.get("type"):
                b["aliases"] = sorted(set(b.get("aliases") or []) | set(n.get("aliases") or []))
                b["source_ids"] = sorted(set(b.get("source_ids") or []) | set(n.get("source_ids") or []))
                if not (b.get("merge_basis") or "").strip() and (n.get("merge_basis") or "").strip():
                    b["merge_basis"] = n["merge_basis"]
                seen_ev = {(x.get("source_id"), x.get("paragraph_id")) for x in b.get("evidence") or []}
                for ev in n.get("evidence") or []:
                    if (ev.get("source_id"), ev.get("paragraph_id")) not in seen_ev:
                        b.setdefault("evidence", []).append(ev)
                        seen_ev.add((ev.get("source_id"), ev.get("paragraph_id")))
                merged.append({"from": nid, "into": nid,
                               "basis": n.get("merge_basis") or b.get("merge_basis")
                                        or "same id, same name and type"})
                remap[nid] = nid
            else:
                k = 2
                new_id = "%s-b" % nid
                while new_id in base_nodes:
                    new_id = "%s-b%d" % (nid, k)
                    k += 1
                conflicting.append({"id": nid, "kept": nid, "new_id": new_id,
                                    "reason": "id collision with a different entity"})
                nn = dict(n)
                nn["id"] = new_id
                out_nodes.append(nn)
                base_nodes[new_id] = nn
                remap[nid] = new_id
            continue
        hit = None
        for k in name_keys(n):
            cand = key_owner.get((k, n.get("type")))
            if cand:
                hit = cand
                break
        if hit and (n.get("merge_basis") or "").strip():
            b = base_nodes[hit]
            b["aliases"] = sorted(set(b.get("aliases") or []) | set(n.get("aliases") or [])
                                  | ({n["name"]} - {b.get("name")}))
            b["source_ids"] = sorted(set(b.get("source_ids") or []) | set(n.get("source_ids") or []))
            b["merge_basis"] = n["merge_basis"]
            merged.append({"from": nid, "into": hit, "basis": n["merge_basis"]})
            remap[nid] = hit
        elif hit:
            conflicting.append({"id": nid, "kept": hit, "new_id": nid,
                                "reason": "same name/type but no merge_basis"})
            out_nodes.append(n)
            base_nodes[nid] = n
            remap[nid] = nid
            skip_pairs.add(_pair(hit, nid))
        else:
            out_nodes.append(n)
            base_nodes[nid] = n
            remap[nid] = nid
            added_nodes.append(nid)

    out_edges = [dict(e) for e in base.get("edges") or []]
    taken = {e.get("id") for e in out_edges}
    for e in edges:
        ee = dict(e)
        ee["source"] = remap.get(ee.get("source"), ee.get("source"))
        ee["target"] = remap.get(ee.get("target"), ee.get("target"))
        eid = ee.get("id")
        if eid in taken:
            k = 2
            while "%s-b%d" % (eid, k) in taken:
                k += 1
            ee["id"] = "%s-b%d" % (eid, k)
            conflicting.append({"id": eid, "kept": eid, "new_id": ee["id"],
                                "reason": "edge id collision"})
        taken.add(ee["id"])
        out_edges.append(ee)
        added_edges.append(ee["id"])
    return out_nodes, out_edges, {"added": {"nodes": added_nodes, "edges": added_edges},
                                  "merged": merged, "conflicting": conflicting,
                                  "skip_pairs": skip_pairs, "remap": remap}


# --------------------------------------------------------------------------
# renderers
# --------------------------------------------------------------------------
def render_queries_md(executed, corpus):
    lines = ["# 查询结果", "",
             "每条查询都真实执行：先按声明的 answer_ids 取节点/边，再收集可解析的证据。", "",
             "| id | 查询 | 命中节点 | 答案证据 | 状态 |",
             "|---|---|---|---|---|"]
    for q in executed:
        ev = q["evidence"]
        ev_txt = "; ".join("%s@%s:%s" % (x["kind"], x["id"], x["paragraph_id"]) for x in ev[:2])
        state = "OK" if ev else ("EMPTY:" + (q["empty_reason"] or "no evidence"))
        lines.append("| %s | %s | %s | %s | %s |"
                     % (q["id"], q["q"].replace("|", "\\|"),
                        ",".join(q["matched_nodes"][:4]) or "-",
                        ev_txt.replace("|", "\\|") or "-", state))
    lines.append("")
    return "\n".join(lines)


def write_graph_csv(path, nodes, edges):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["# section: nodes"])
    w.writerow(["id", "name", "type", "source_ids", "aliases", "merge_basis"])
    for n in nodes:
        w.writerow([n.get("id"), n.get("name"), n.get("type") or "",
                    ";".join(n.get("source_ids") or []),
                    ";".join(n.get("aliases") or []), n.get("merge_basis") or ""])
    w.writerow([])
    w.writerow(["# section: edges"])
    w.writerow(["id", "source", "relation", "target", "source_id",
                "paragraph_id", "quote", "conditions"])
    for e in edges:
        w.writerow([e.get("id"), e.get("source"), e.get("relation"), e.get("target"),
                    e.get("source_id"), e.get("paragraph_id"), e.get("quote"),
                    e.get("conditions") or ""])
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())


# --------------------------------------------------------------------------
# main run
# --------------------------------------------------------------------------
def run(case, materials, out_dir, draft=None, base=None):
    corpus = load_corpus(materials)
    if not corpus["papers"]:
        return {"status": "failed", "main": {}, "errors": [{"code": "no_material"}],
                "warnings": [], "queries": [], "graph": {}}

    nodes = list((draft or {}).get("nodes") or []) if isinstance(draft, dict) else []
    edges = list((draft or {}).get("edges") or []) if isinstance(draft, dict) else []
    queries = list((draft or {}).get("queries") or []) if isinstance(draft, dict) else []

    incremental = None
    skip_pairs = set()
    if base:
        nodes, edges, incremental = merge_incremental(base, nodes, edges)
        skip_pairs = incremental.pop("skip_pairs", set())
        remap = incremental.pop("remap", {})
        for q in queries:
            if isinstance(q, dict) and q.get("answer_ids"):
                q["answer_ids"] = [remap.get(a, a) for a in q["answer_ids"]]

    if not draft or not nodes:
        cand = candidates(corpus)
        graph = {"meta": {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
                          "mode": "candidates", "papers": _paper_meta(corpus)},
                 "nodes": cand, "edges": []}
        sk.jdump(os.path.join(out_dir, "graph.json"), graph)
        write_graph_csv(os.path.join(out_dir, "graph.csv"), cand, [])
        with open(os.path.join(out_dir, "queries.md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# 查询结果\n\n尚未构建图谱，没有可执行的查询。\n")
        checks = {"errors": [], "warnings": [{"code": "draft_absent",
                                              "detail": "no draft graph; candidate entities only"}],
                  "summary": {"nodes": len(cand), "edges": 0, "queries": 0}}
        sk.jdump(os.path.join(out_dir, "checks.json"), checks)
        return {"status": "partial", "main": {"graph": graph, "queries": [], "checks": checks,
                                              "metrics": {"nodes": len(cand), "edges": 0,
                                                          "evidence_resolved": 0, "merged": 0,
                                                          "conflicts": 0, "queries": 0}},
                "errors": [], "warnings": checks["warnings"], "queries": [], "graph": graph,
                "corpus": corpus}

    nodes_by_id = {}
    for n in nodes:
        nodes_by_id[n.get("id")] = n

    err_ev, resolved = check_edges(edges, nodes_by_id, corpus["papers"])
    err_nn, warn_nn = check_node_evidence(nodes, corpus["papers"])
    err_mg, warn_mg, conflicts = check_merges(nodes, skip_pairs)
    err_ov = check_overreach(edges, nodes_by_id, resolved)
    executed = run_queries(queries, nodes, edges, resolved)
    err_q = check_queries(queries, executed)
    warn_orphan = check_orphans(nodes, edges)

    errors = err_ev + err_nn + err_mg + err_ov + err_q
    warnings = warn_nn + warn_mg + warn_orphan
    if incremental:
        for c in incremental["conflicting"]:
            warnings.append({"code": "incremental_conflict", "id": c["id"],
                             "detail": "%s (kept %s, new id %s)"
                                       % (c["reason"], c["kept"], c["new_id"])})

    merged_nodes = sum(1 for n in nodes if (n.get("merge_basis") or "").strip()
                       or n.get("merged_from"))
    if incremental:
        merged_nodes += len(incremental["merged"])
    metrics = {"nodes": len(nodes), "edges": len(edges),
               "evidence_resolved": sum(1 for v in resolved.values() if v),
               "merged": merged_nodes, "conflicts": len(conflicts),
               "queries": len(queries)}
    status = "partial" if errors else "success"

    graph = {"meta": {"case_id": sk.case_id_of(case, [m["path"] for m in materials]),
                      "mode": "incremental" if base else "draft",
                      "papers": _paper_meta(corpus),
                      "paragraph_ids": "JATS paragraph_id, not PDF page numbers",
                      "incremental": incremental},
             "nodes": nodes, "edges": edges}
    sk.jdump(os.path.join(out_dir, "graph.json"), graph)
    write_graph_csv(os.path.join(out_dir, "graph.csv"), nodes, edges)
    qmd = render_queries_md(executed, corpus)
    with open(os.path.join(out_dir, "queries.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(qmd)

    checks = {"errors": errors, "warnings": warnings,
              "conflicts": conflicts, "queries": executed,
              "incremental": incremental,
              "summary": {"nodes": len(nodes), "edges": len(edges),
                          "evidence_resolved": metrics["evidence_resolved"],
                          "n_errors": len(errors), "n_warnings": len(warnings),
                          "merged": metrics["merged"], "conflicts": metrics["conflicts"],
                          "queries": len(queries)}}
    sk.jdump(os.path.join(out_dir, "checks.json"), checks)
    return {"status": status, "main": {"graph": graph, "queries": executed,
                                       "checks": checks, "metrics": metrics},
            "errors": errors, "warnings": warnings, "queries": executed,
            "graph": graph, "corpus": corpus, "incremental": incremental,
            "paragraphs_used": sorted({"%s/%s" % (e.get("source_id"), e.get("paragraph_id"))
                                       for e in edges})}


def _paper_meta(corpus):
    out = []
    for pid in corpus["order"]:
        p = corpus["papers"][pid]
        m = corpus["meta"].get(pid, {})
        out.append({"paper_id": pid, "title": p["title"] or m.get("title", ""),
                    "doi": p["doi"] or m.get("doi", ""), "file": p["file"],
                    "license": m.get("license", ""),
                    "source_hash": m.get("source_hash", ""),
                    "paragraphs": len(p["paragraphs"])})
    return out
