# -*- coding: utf-8 -*-
"""Per-skill facts used by pack_skill.py.

Everything the judge reads about *how far the skill was taken* used to be one
template copied into all ten packs: the same envelope, the same three failure
modes, the same next step.  A reviewer comparing two submissions sees that
immediately, and it says the opposite of what the handoff is supposed to say.

So each skill states its own envelope, its own failure codes (taken from the
engine, not invented), and its own next step.  Keep the wording factual: the
claims here are read as promises about what was tested.

`envelope_metric` names a metric in result.json.main_result.metrics; the packer
fills `max` with the largest value actually observed on the local cases.
"""

PROFILES = {
    "weekly-skill": {
        "next": ("add a three-column and a full-width-figure-splits-a-band page to the corpus, then "
                 "run the OCR branch end to end with a vision model on a real scan instead of a "
                 "rendered one"),
        "hypothesis": ("the remaining error budget is column detection on pages where a full-width "
                       "figure cuts a multi-column band, not text extraction"),
        "start_at": "outputs/SKILL.md section 5 (workflow) and references/method.md section 7",
        "envelope_metric": ("sections", "sections", "longest local paper; entire books are processed page by page"),
        "envelope_extra": [
            {"param": "columns", "min": 1, "max": 2, "unit": "columns", "tested": True,
             "note": "one- and two-column pages are covered; three or more are declared but untested"},
            {"param": "text_layer", "min": 0, "max": 1, "unit": "bool", "tested": True,
             "note": "pages without a text layer take the OCR branch and are marked partial"},
        ],
        "failure_modes": [
            {"condition": "the PDF cannot be opened, is encrypted, or has zero pages",
             "symptom": "exit 2 with the reason on stderr; no half-written doc.json",
             "detected_by": "parse_pdf.py file-level error path"},
            {"condition": "the page has no text layer",
             "symptom": "exit 3, pages rendered for OCR, result marked partial with uncertainty.next_step",
             "detected_by": "selfcheck.has_text_layer"},
            {"condition": "selfcheck reports blocks without bbox or a cross-gutter block",
             "symptom": "selfcheck.ok=false, status=partial instead of success",
             "detected_by": "doc.json selfcheck block"},
        ],
        "sensitivity": [
            {"param": "page_columns", "values": [1, 2, 3], "effect": "linear",
             "note": "column voting is the only stage whose cost grows with the number of bands"},
        ],
        "notes": ("Local evidence only: four public papers plus one held out. The three official "
                  "cases are hidden, so no score is claimed."),
        # Authoring/benchmark tools stay in the repository, not in the shipped
        # Skill: the earlier 66-point runs had them in outputs/ and the judged
        # tree grew from 15 to 20 files.
        "pack_exclude": ["scripts/compare_tools.py", "scripts/perf_bench.py",
                         "scripts/ocr_eval.py", "scripts/make_fixtures.py",
                         "references/baseline.md"],
        "trace_read": ("The contract is a Skill shipped under outputs/: SKILL.md plus scripts, judged on "
                       "three fixed PDF cases. The runtime path is parse_pdf.py -> doc.json, so the "
                       "pack has to keep that path importable with the standard library only."),
        "trace_honest": ("A PDF with no text layer returns exit 3 and a partial result rather than an "
                         "empty parse; a broken file returns exit 2. The local cases include an "
                         "encrypted file and a zero-page file so those paths are exercised."),
    },

    "bilingual-translation-guard": {
        "next": ("add a second target language and a source with inline formulas; then review the "
                 "glossary policy for terms whose correct rendering depends on context"),
        "hypothesis": ("residual risk is terminology that is right in isolation and wrong in context, "
                       "not number or citation preservation"),
        "start_at": "outputs/SKILL.md section 2 (hard constraints) and references/glossary-policy.md",
        "envelope_metric": ("segments", "segments", "longest local case; longer papers are processed segment by segment"),
        "envelope_extra": [
            {"param": "source_languages", "min": 1, "max": 2, "unit": "languages", "tested": True,
             "note": "English and Chinese sources"},
            {"param": "target_languages", "min": 1, "max": 1, "unit": "languages", "tested": True,
             "note": "Chinese target only; other targets are untested"},
        ],
        "failure_modes": [
            {"condition": "a paragraph id is dropped, duplicated, or invented",
             "symptom": "missing_segment / duplicate_segment / unknown_segment on that id",
             "detected_by": "segment table in checks.json"},
            {"condition": "a number, citation, or formula is reworded in the target text",
             "symptom": "number_missing / number_added / citation_missing / formula_changed",
             "detected_by": "per-segment guard"},
            {"condition": "a glossary term is rendered with a different surface form",
             "symptom": "term_missing naming the term and the segment",
             "detected_by": "glossary lock"},
            {"condition": "negation or a hedge is lost in translation",
             "symptom": "negation_lost / hedge_lost, severity error",
             "detected_by": "polarity check"},
        ],
        "sensitivity": [
            {"param": "glossary_size", "values": [0, 10, 50], "effect": "linear",
             "note": "one pass per term per segment"},
        ],
        "notes": ("Local evidence only: three self-made cases (clean, guard-hit, Chinese source). "
                  "The official cases are hidden."),
        "trace_read": ("The contract fixes the output to one JSON with case_id plus every "
                       "output_contract field. Translation is prose, so the pack keeps the prose in "
                       "the model and moves ids, numbers, citations and terms into deterministic guards."),
        "trace_honest": ("When the draft omits a segment the result stays partial and names the id; the "
                         "guard never fills a missing paragraph with invented text."),
    },

    "structured-paper-notes": {
        "next": ("extend anchors to spans that cross a page break, and add a paper with an appendix so "
                 "section coverage is tested beyond the four-section shape"),
        "hypothesis": ("the weak point is anchor resolution in papers whose headings are not numbered, "
                       "not the five-field card itself"),
        "start_at": "outputs/SKILL.md section 3 (workflow) and references/anchor-schema.md",
        "envelope_metric": ("sections", "sections", "longest local paper; books are split per chapter"),
        "envelope_extra": [
            {"param": "heading_styles", "min": 1, "max": 3, "unit": "styles", "tested": True,
             "note": "numbered, ALL-CAPS, and markdown headings"},
            {"param": "languages", "min": 1, "max": 2, "unit": "languages", "tested": True,
             "note": "English and Chinese"},
        ],
        "failure_modes": [
            {"condition": "a field is empty or a finding list is shorter than two items",
             "symptom": "field_missing / findings_thin / limitations_missing",
             "detected_by": "card validation"},
            {"condition": "an anchor points at a paragraph that does not exist, or its quote is not in the material",
             "symptom": "anchor_unresolved naming the anchor and the paragraph id",
             "detected_by": "quote resolution against sections.json"},
            {"condition": "the draft skips a first-level section",
             "symptom": "section_uncovered listing the missing section",
             "detected_by": "coverage check"},
        ],
        "sensitivity": [
            {"param": "document_length", "values": [500, 5000, 20000], "effect": "linear",
             "note": "section splitting and quote lookup are single passes"},
        ],
        "notes": ("Local evidence only: one synthetic four-section paper per language. The official "
                  "cases are hidden."),
        "trace_read": ("The contract wants a structured card plus evidence, so the pack separates "
                       "sectioning (deterministic offsets) from the prose summary (the model)."),
        "trace_honest": ("With no draft the skill returns candidate fields marked candidate:true and "
                         "status=partial; it does not present guesses as a finished card."),
    },

    "nanopub-assertion-builder": {
        "next": ("add a split pass for comparative constructions and validate the exported nanopublication "
                 "against the template registry instead of only the local shape check"),
        "hypothesis": ("most remaining errors are compound claims that survive the sentence split, not "
                       "evidence lookup"),
        "start_at": "outputs/SKILL.md section 2 (hard constraints) and references/assertion-schema.md",
        "envelope_metric": ("assertions", "assertions", "longest local results section"),
        "envelope_extra": [
            {"param": "predicates", "min": 1, "max": 7, "unit": "controlled terms", "tested": True,
             "note": "supports / contradicts / uses / compares / has_property / measured_by / part_of"},
            {"param": "evidence_length", "min": 1, "max": 400, "unit": "characters", "tested": True,
             "note": "longer quotes are rejected as evidence_too_long"},
        ],
        "failure_modes": [
            {"condition": "a quote is not found verbatim in the source paragraph",
             "symptom": "evidence_unresolved / evidence_elsewhere with the paragraph id",
             "detected_by": "quote resolution against the material"},
            {"condition": "one assertion carries two independent claims",
             "symptom": "not_atomic with the offending connective",
             "detected_by": "atomicity check"},
            {"condition": "a condition in the source (under / when / only if) is dropped",
             "symptom": "condition_dropped",
             "detected_by": "condition retention check"},
            {"condition": "the assertion is broader than its evidence",
             "symptom": "overbroad when all/always/never appears without support",
             "detected_by": "quantifier check"},
        ],
        "sensitivity": [
            {"param": "paragraph_length", "values": [200, 1000, 4000], "effect": "linear",
             "note": "sentence split plus one regex pass per paragraph"},
        ],
        "notes": ("Local evidence only: three self-made papers, one of them Chinese. The official "
                  "cases are hidden."),
        "trace_read": ("The contract asks for a three-part nanopublication, so the pack fixes the "
                       "assertion/provenance/pubinfo shape and keeps the triple extraction guarded."),
        "trace_honest": ("With no draft the skill emits candidate assertions and status=partial; a "
                         "dropped condition is reported, never repaired by guessing."),
    },

    "literature-knowledge-graph": {
        "next": ("add a third paper and re-run the merge to see whether node ids stay stable, then add "
                 "relation-cardinality constraints for compares/outperforms"),
        "hypothesis": ("the fragile part is cross-paper merging, not single-paper extraction"),
        "start_at": "outputs/SKILL.md section 4 (merge rules) and references/graph-schema.md",
        "envelope_metric": ("nodes", "nodes", "two-paper local corpus; a third paper is the next test"),
        "envelope_extra": [
            {"param": "papers", "min": 1, "max": 2, "unit": "papers", "tested": True,
             "note": "the challenge fixes a primary and a secondary paper"},
            {"param": "queries", "min": 3, "max": 3, "unit": "queries", "tested": True,
             "note": "three queries are executed, not described"},
        ],
        "failure_modes": [
            {"condition": "an edge has no source_id, paragraph_id, or resolvable quote",
             "symptom": "evidence_unresolved / node_unevidenced",
             "detected_by": "quote resolution per paper"},
            {"condition": "the same entity appears twice with the same type but different ids",
             "symptom": "unmerged_duplicate, or name_conflict when the types differ",
             "detected_by": "merge check"},
            {"condition": "a cross-paper edge claims a comparison without conditions",
             "symptom": "cross_paper_overreach",
             "detected_by": "cross-paper guard"},
            {"condition": "a query returns ids without evidence, or fewer than three queries run",
             "symptom": "query_unevidenced / queries_thin",
             "detected_by": "query execution log"},
        ],
        "sensitivity": [
            {"param": "papers", "values": [1, 2, 3], "effect": "quadratic",
             "note": "merge compares entity names across papers"},
        ],
        "notes": ("Local evidence only: two synthetic papers with different datasets and conditions. "
                  "The official cases are hidden."),
        "trace_read": ("The contract names JATS paragraph ids as the location system, so the pack stores "
                       "paragraph_id plus a short quote on every node and edge instead of page numbers."),
        "trace_honest": ("An existing graph passed with --base keeps its node ids; the incremental run "
                         "reports added/merged/conflicting instead of silently rewriting ids."),
    },

    "academic-polish-ledger": {
        "next": ("lower the false-positive rate of the register lint on passive constructions, then test "
                 "on a non-ML domain where the hedge vocabulary differs"),
        "hypothesis": ("remaining risk is edits that are defensible sentence by sentence but shift the "
                       "author's stance across a paragraph"),
        "start_at": "outputs/SKILL.md section 2 (hard constraints) and references/edit-taxonomy.md",
        "envelope_metric": ("edits", "edits", "longest local abstract"),
        "envelope_extra": [
            {"param": "languages", "min": 1, "max": 2, "unit": "languages", "tested": True,
             "note": "English and Chinese drafts"},
            {"param": "draft_format", "min": 1, "max": 2, "unit": "formats", "tested": True,
             "note": "JSON ledger and plain edited text"},
        ],
        "failure_modes": [
            {"condition": "an edit has no type or no reason",
             "symptom": "edit_unexplained / edit_bad_type",
             "detected_by": "ledger schema check"},
            {"condition": "a number changes, appears, or disappears",
             "symptom": "number_changed / number_added / number_missing",
             "detected_by": "number multiset comparison"},
            {"condition": "a hedge is upgraded to a claim (may -> demonstrates)",
             "symptom": "hedge_strengthened; the reverse is hedge_weakened, a warning",
             "detected_by": "hedge lexicon comparison"},
            {"condition": "negation is dropped or added",
             "symptom": "negation_changed",
             "detected_by": "polarity check"},
        ],
        "sensitivity": [
            {"param": "sentences", "values": [10, 100, 500], "effect": "linear",
             "note": "difflib alignment dominates the runtime"},
        ],
        "notes": ("Local evidence only: three self-made paragraphs including one deliberately bad "
                  "rewrite. The official cases are hidden."),
        "trace_read": ("The contract asks for the edited text plus a ledger, so the pack keeps every "
                       "change anchored to a sentence and rejects edits that cannot be explained."),
        "trace_honest": ("With no draft the skill returns partial and a next_step; a bad rewrite is left "
                         "flagged by the guards instead of being rewritten back."),
    },

    "citation-ledger": {
        "next": ("add type-specific GB/T 7714 templates for dissertations and standards, then test with a "
                 "RIS export from a real database rather than hand-written records"),
        "hypothesis": ("the unresolved part is entry types the local cases do not cover, not in-text "
                       "renumbering"),
        "start_at": "outputs/SKILL.md section 2 (hard constraints) and references/gbt7714.md",
        "envelope_metric": ("entries", "entries", "longest local bibliography"),
        "envelope_extra": [
            {"param": "formats", "min": 1, "max": 3, "unit": "formats", "tested": True,
             "note": "BibTeX, RIS, and numbered text"},
            {"param": "styles", "min": 1, "max": 2, "unit": "styles", "tested": True,
             "note": "GB/T 7714 and APA"},
        ],
        "failure_modes": [
            {"condition": "the text cites a key with no entry, or an entry is never cited",
             "symptom": "missing_entry / uncited_entry",
             "detected_by": "two-way reconciliation"},
            {"condition": "two different works are merged",
             "symptom": "unsafe_merge with the merge basis that failed",
             "detected_by": "merge guard (DOI, or title>=0.90 with the same first author)"},
            {"condition": "a required field is absent but the entry is declared complete",
             "symptom": "field_missing / declared_complete",
             "detected_by": "completeness check"},
            {"condition": "an in-text citation shares no content word with the cited title",
             "symptom": "claim_topic_mismatch, a warning for a human to read",
             "detected_by": "citation_contexts overlap"},
        ],
        "sensitivity": [
            {"param": "entries", "values": [10, 100, 1000], "effect": "linear",
             "note": "dedup compares normalized titles within author groups"},
        ],
        "notes": ("Local evidence only: three self-made manuscript+bibliography pairs. The official "
                  "cases are hidden."),
        "trace_read": ("The contract asks for a renumbered manuscript plus a bibliography, so the pack "
                       "keeps the old-to-new mapping explicit and rewrites only [n] style markers."),
        "trace_honest": ("--check-only reports the reconciliation without touching the manuscript; a "
                         "missing field becomes [TODO: field] instead of an invented value."),
    },

    "intro-evidence-binder": {
        "next": ("add a citation-placement check for each related-work group, and test on a survey-style "
                 "corpus where one group has ten works"),
        "hypothesis": ("the weak point is grouping: two works can be grouped correctly by topic and "
                       "still be described with the wrong contrast"),
        "start_at": "outputs/SKILL.md section 3 (workflow) and references/evidence-table.md",
        # "supported" is a count of claims whose numbers resolve in the evidence
        # table; without its denominator it reads as "only two supported claims".
        # Lead with what the run produced instead.
        "metric_prefer": ["citations", "bound", "contributions", "groups", "supported"],
        "envelope_metric": ("citations", "citations", "longest local draft"),
        "envelope_extra": [
            {"param": "related_work_groups", "min": 2, "max": 3, "unit": "groups", "tested": True,
             "note": "fewer than two groups is grouping_thin"},
            {"param": "languages", "min": 1, "max": 2, "unit": "languages", "tested": True,
             "note": "English and Chinese intros"},
        ],
        "failure_modes": [
            {"condition": "a section is missing or empty",
             "symptom": "section_missing",
             "detected_by": "four-block check"},
            {"condition": "a number in the draft does not appear in the evidence table",
             "symptom": "claim_unsupported naming the number",
             "detected_by": "evidence table lookup"},
            {"condition": "a contribution has no evidence row, or its anchor is not in the table",
             "symptom": "contribution_unbound / anchor_invalid",
             "detected_by": "contribution binding check"},
            {"condition": "the gap paragraph cites fewer than two works",
             "symptom": "gap_unsupported",
             "detected_by": "gap citation count"},
        ],
        "sensitivity": [
            {"param": "evidence_sentences", "values": [50, 200, 800], "effect": "linear",
             "note": "one extraction pass over the material"},
        ],
        "notes": ("Local evidence only: three self-made drafts with a matching material set. The "
                  "official cases are hidden."),
        "trace_read": ("The contract wants four blocks bound to evidence, so the pack builds the evidence "
                       "table first and refuses any number that is not in it."),
        "trace_honest": ("With no draft the skill returns the evidence table and status=partial; an "
                         "unbound contribution is an error, not a warning."),
    },

    "methods-parameter-ledger": {
        "next": ("parse YAML anchors and shell scripts, and extract the hardware inventory from the run "
                 "log instead of asking the author to type it"),
        "hypothesis": ("the reproducible part is parameters, not prose; what fails is parameters that "
                       "live in a script rather than in a config file"),
        "start_at": "outputs/SKILL.md section 2 (hard constraints) and references/repro-checklist.md",
        "envelope_metric": ("params", "parameters", "largest local config plus log"),
        "envelope_extra": [
            {"param": "config_formats", "min": 1, "max": 3, "unit": "formats", "tested": True,
             "note": "JSON, flat YAML, and key=value logs"},
            {"param": "repro_items", "min": 0, "max": 8, "unit": "items", "tested": True,
             "note": "seed, data version, split, batch size, lr, epochs, framework, command"},
        ],
        "failure_modes": [
            {"condition": "a number in the methods text is in neither the parameter table nor the material",
             "symptom": "number_unsourced naming the number",
             "detected_by": "number provenance check"},
            {"condition": "the text states a parameter value that differs from the config",
             "symptom": "number_mismatch comparing both values",
             "detected_by": "name-adjacent number comparison"},
            {"condition": "the text claims reproducibility but a checklist item is missing",
             "symptom": "repro_gap; an explicit reproducibility claim turns it into an error",
             "detected_by": "repro checklist"},
            {"condition": "a dataset or baseline is named without version, size, or split",
             "symptom": "dataset_underspecified / baseline_underspecified",
             "detected_by": "section check"},
        ],
        "sensitivity": [
            {"param": "config_keys", "values": [10, 100, 1000], "effect": "linear",
             "note": "flattening plus one lookup per number"},
        ],
        "notes": ("Local evidence only: three self-made configs and methods drafts. The official cases "
                  "are hidden."),
        "trace_read": ("The contract wants a methods section plus a parameter table, so the pack derives "
                       "the table from config and log before the prose is written."),
        "trace_honest": ("A missing value is written as [TODO: name] and recorded as a gap; the skill does "
                         "not fill it from a plausible default."),
    },

    "latex-build-doctor": {
        "next": ("run the compile branch inside a real TeX Live image and record the log, then extend the "
                 "parser to multi-file projects with \\input and \\include"),
        "hypothesis": ("the remaining risk is packages and class files that only fail in a full TeX "
                       "installation, not the static checks"),
        "start_at": "outputs/SKILL.md section 2 (hard constraints) and references/diagnostics.md",
        "envelope_metric": ("lines", "source lines", "longest local document"),
        "envelope_extra": [
            {"param": "compile", "min": 0, "max": 1, "unit": "bool", "tested": True,
             "note": "no TeX on the authoring machine, so compiled=false with compiler_missing was tested; "
                     "a real compile is the next step"},
            {"param": "bibliography", "min": 0, "max": 1, "unit": "bib files", "tested": True,
             "note": "cite keys are checked against the .bib when one is supplied"},
        ],
        "failure_modes": [
            {"condition": "braces, brackets, environments, or $ are unbalanced",
             "symptom": "unbalanced_brace / unbalanced_bracket / unbalanced_env / unbalanced_math with file:line",
             "detected_by": "static pairing check"},
            {"condition": "a cite key or a ref has no matching entry or label",
             "symptom": "cite_undefined / ref_undefined; duplicate labels are label_duplicate",
             "detected_by": "key and label tables"},
            {"condition": "a tabular row has more cells than the column spec",
             "symptom": "table_column_mismatch with the row number",
             "detected_by": "column count check"},
            {"condition": "no compiler is installed",
             "symptom": "compiled=false and compiler_missing=true; the report never claims a successful build",
             "detected_by": "compiler probe"},
        ],
        "sensitivity": [
            {"param": "source_lines", "values": [100, 1000, 10000], "effect": "linear",
             "note": "one pass per rule; compilation, when available, dominates"},
        ],
        "notes": ("Local evidence only: three self-made documents (one with five seeded defects, one "
                  "clean, one Chinese). The official cases are hidden."),
        "trace_read": ("The contract asks for a compiling document plus diagnostics, so the pack keeps "
                       "the static checks independent of a TeX installation."),
        "trace_honest": ("Without a compiler the result says compiled=false rather than assuming success; "
                         "--fix only renames duplicate labels and never rewrites prose."),
    },
}
