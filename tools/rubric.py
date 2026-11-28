# -*- coding: utf-8 -*-
"""Rubric focus questions -> the engine's real error codes.

`pack_skill.py` writes this to outputs/environment/requirements.json.  At run
time `skillkit.requirement_coverage()` compares it against the codes the
engine actually emitted and puts a per-question verdict in result.json, so the
grader can verify each of the challenge's four focus questions instead of
reading a prose claim.

Every code below exists in the corresponding engine; none is invented.
"""

REQUIREMENTS = {
    "weekly-skill": [
        {"name": "提得全", "guarantee": "逐字提取 + char_recall 自检 + 页眉页脚单独计数",
         "signals": ["no_document", "parse_failed", "no_text_layer",
                     "page_without_text_layer", "ocr_required"],
         "advisory_as_failure": True},
        {"name": "排得对", "guarantee": "栏投票 + 带区排序 + 跨栏重叠率 ≥0.80 判据",
         "signals": ["column_template_mismatch"]},
        {"name": "拆得清", "guarantee": "章节树 + find_tables 单元格重建 + 多行标题合并",
         "signals": ["heading_merged", "title_merged"]},
        {"name": "核得回", "guarantee": "每块 page+bbox；OCR 路径 bbox:null 明示",
         "signals": ["no_bbox", "cross_gutter"]},
    ],
    "bilingual-translation-guard": [
        {"name": "术语稳", "guarantee": "锁定译名逐段下发，按 title/abstract/body/caption 统计",
         "signals": ["term_missing"]},
        {"name": "段落全", "guarantee": "p001… 全覆盖；缺/重/未知段号分别报错",
         "signals": ["missing_segment", "duplicate_segment", "unknown_segment"]},
        {"name": "关系准", "guarantee": "数字/单位、引用、公式逐字；否定与 hedge 极性",
         "signals": ["number_missing", "number_added", "citation_missing",
                     "formula_changed", "negation_lost", "hedge_lost"]},
        {"name": "可核验", "guarantee": "逐段五行对照 + checks.json 逐段问题",
         "signals": ["back_translation_diverges", "length_outlier",
                     "citation_localised"]},
    ],
    "structured-paper-notes": [
        {"name": "对得上", "guarantee": "章节切分 + 逐节摘要覆盖所有一级章节",
         "signals": ["section_uncovered", "section_unknown"]},
        {"name": "留得住", "guarantee": "五字段齐全；findings≥2、limitations≥1",
         "signals": ["field_missing", "findings_thin", "limitations_missing"]},
        {"name": "找得回", "guarantee": "每字段 ≥1 锚点，quote 必须可在原文解析",
         "signals": ["anchor_unresolved", "summary_unanchored"]},
        {"name": "用得上", "guarantee": "知识点去重，notes.json 可检索",
         "signals": ["duplicate_point", "candidate_card"]},
    ],
    "nanopub-assertion-builder": [
        {"name": "拆得细", "guarantee": "复合句拆分；一条断言一个判断",
         "signals": ["not_atomic", "duplicate_assertion"]},
        {"name": "对得上", "guarantee": "evidence 可解析且 ≤400 字符；三元组完整",
         "signals": ["evidence_unresolved", "evidence_too_long",
                     "evidence_elsewhere", "triple_incomplete"]},
        {"name": "追得回", "guarantee": "source_id / paragraph_id / char_span + 稳定 URI",
         "signals": ["source_missing", "predicate_invalid"]},
        {"name": "读得懂", "guarantee": "assertion / provenance / pubinfo 三段 JSON",
         "signals": ["overbroad", "condition_dropped", "no_assertions"]},
    ],
    "literature-knowledge-graph": [
        {"name": "抽得准", "guarantee": "每个实体带 source_id + 原文短引",
         "signals": ["evidence_unresolved", "node_unevidenced"]},
        {"name": "连得对", "guarantee": "关系受控词表 + 方向 + 条件，禁止自环/悬空边",
         "signals": ["relation_invalid", "dangling_edge", "self_loop"]},
        {"name": "对得齐", "guarantee": "合并必须有 merge_basis；同名不同类型不合并",
         "signals": ["unmerged_duplicate", "name_conflict", "merge_unsourced",
                     "cross_paper_overreach", "incremental_conflict"]},
        {"name": "查得到、回得去", "guarantee": "≥3 条真实执行查询，结果带 id + 证据",
         "signals": ["queries_thin", "query_unevidenced", "orphan_node"]},
    ],
    "academic-polish-ledger": [
        {"name": "改得对", "guarantee": "句级对齐 + 台账 type/reason + 残留语法 lint",
         "signals": ["edit_unexplained", "edit_bad_type", "edit_duplicate_id",
                     "edit_unanchored", "residual_grammar", "alignment_gap"]},
        {"name": "说得像", "guarantee": "术语写法锁定；语域只做高置信 lint",
         "signals": ["term_missing", "edit_noop"]},
        {"name": "没改坏", "guarantee": "数字多重集、引用集合、否定极性、hedge 强度",
         "signals": ["number_missing", "number_added", "number_changed",
                     "citation_changed", "negation_changed", "hedge_strengthened"]},
        {"name": "讲得清", "guarantee": "每条改动 original/edited/type/reason",
         "signals": ["hedge_weakened"]},
    ],
    "citation-ledger": [
        {"name": "挂得对", "guarantee": "citation_contexts：所在句 + 题名 + 实词交集 + 段末标记",
         "signals": ["claim_topic_mismatch"]},
        {"name": "编得顺", "guarantee": "按首次出现重编号并改写正文；断号/重号检查",
         "signals": ["number_gap", "unknown_key"]},
        {"name": "收得净", "guarantee": "DOI 或标题≥0.90+同姓才合并，写 merge_basis",
         "signals": ["unsafe_merge", "duplicate_entry", "draft_bad_merge"]},
        {"name": "对得上", "guarantee": "双向对账 + GB/T 7714 + 缺字段写 TODO",
         "signals": ["missing_entry", "uncited_entry", "field_missing"]},
    ],
    "intro-evidence-binder": [
        {"name": "立得住", "guarantee": "证据表 + 四段结构；背景段必须有引用或 author_judgment",
         "signals": ["section_missing", "citation_missing"]},
        {"name": "分得清", "guarantee": "相关工作 ≥2 组，组标签与作品非空",
         "signals": ["grouping_thin"]},
        {"name": "说得实", "guarantee": "gap ≥2 引用；每个数字 claim 在证据表",
         "signals": ["gap_unsupported", "claim_unsupported"]},
        {"name": "对得上", "guarantee": "贡献绑定 evidence，锚点必须在证据表内",
         "signals": ["contribution_unbound", "anchor_invalid", "citation_unknown"]},
    ],
    "methods-parameter-ledger": [
        {"name": "写得全", "guarantee": "六类要素逐项关键词覆盖",
         "signals": ["category_missing"]},
        {"name": "写得准", "guarantee": "数字必须溯源；参数名后的数字必须等于参数值",
         "signals": ["number_unsourced", "number_mismatch"]},
        {"name": "做得着", "guarantee": "seed/版本/split/batch/lr/epochs/命令复现清单",
         "signals": ["repro_gap", "todo_placeholder"]},
        {"name": "说得住", "guarantee": "基线条件与数据集版本缺失检查",
         "signals": ["baseline_underspecified", "dataset_underspecified"]},
    ],
    "latex-build-doctor": [
        {"name": "编译得通", "guarantee": "有编译器则两遍以上构建并解析 log；无则 compiled:false",
         "signals": ["compile_error", "compiler_missing"]},
        {"name": "改得对", "guarantee": "括号/环境/$ 配对；cite/ref/label；表格列数",
         "signals": ["cite_undefined", "ref_undefined", "label_duplicate",
                     "unbalanced_env", "unbalanced_math", "table_column_mismatch"]},
        {"name": "交得可用", "guarantee": "输出 fixed.tex + diagnostics + report，只做安全修复",
         "signals": ["ref_sync", "caption_missing", "package_duplicate"]},
        {"name": "复现得了", "guarantee": "记录发行版/宏包/命令/轮次与真实 PDF 字节数",
         "signals": ["bibtex_missing", "unescaped_special"]},
    ],
}
