# Scientific reading & writing skills (Bohrium product-arena)

Ten self-contained Agent Skills. Each directory has `SKILL.md`, `environment/resources.yaml`,
a deterministic engine under `scripts/`, references, one example, and three self-made local cases.
They are written for the runtime contract used by the arena: read `/input/case.json`, write
`/app/output/result.json` with `case_id` and every `output_contract` field.

| Skill | Challenge | Title | local checks |
|---|---|---|---|
| [reading-01-pdf](reading-01-pdf/) | `product-arena-08-3027d350` | 阅读01｜文献文档解析 | 17 |
| [reading-03-translation](reading-03-translation/) | `product-arena-01-5a9928c1` | 阅读03｜文献翻译 | 15 |
| [reading-10-notes](reading-10-notes/) | `product-arena-06-6d8cf72b` | 阅读10｜文献总结与结构化笔记 | 21 |
| [reading-14-nanopub](reading-14-nanopub/) | `product-arena-09-0e8befd4` | 阅读14｜Nanopublication | 22 |
| [reading-15-kg](reading-15-kg/) | `product-arena-10-760d1a0b` | 阅读15｜文献知识图谱构建 | 19 |
| [writing-02-polish](writing-02-polish/) | `product-arena-02-7051d92d` | 写作02｜学术语言润色 | 30 |
| [writing-04-references](writing-04-references/) | `product-arena-03-429cc14d` | 写作04｜参考文献与引用管理 | 36 |
| [writing-08-intro](writing-08-intro/) | `product-arena-04-4b82ad21` | 写作08｜引言与相关工作写作 | 15 |
| [writing-09-methods](writing-09-methods/) | `product-arena-05-64faa4a2` | 写作09｜方法与实验章节写作 | 15 |
| [writing-13-latex](writing-13-latex/) | `product-arena-07-865de7e4` | 写作13｜LaTeX 写作与编译 | 23 |

## Design rule shared by all ten

A language model does the language work; the scripts do everything that must not be left to a
language model: stable ids, byte-level preservation of numbers/citations/formulas, controlled
vocabularies, evidence quotes that must resolve in the source, and an honest `status` field.
If a draft is missing, the skill returns `partial` with a `next_step` instead of inventing output.

## Honest scope

The three cases in each `tests/cases/` are self-made pipeline tests, not the platform's hidden
cases. No benchmark score is claimed in this repository.
