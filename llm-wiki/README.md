# llm-wiki — an AI-native knowledge base with citations, permissions and human review

A small, working LLM Wiki: knowledge lives as markdown pages with governance
metadata, an **ask agent** answers only from pages the user may read and cites
every claim, a **curator agent** turns new source documents into *draft* pages,
and nothing becomes authoritative until a human approves it. A **linter** finds
stale pages, contradictions and broken links, and an **eval** checks that the
right page is retrieved for the right people.

The demo content is a fictional public funding programme (the "Nordlicht
Innovation Grant") with an archived 2025 rate sheet, a finance-only audit page and
one deliberately planted contradiction, so every feature has something to show.

```
sources/  ──propose──►  drafts/  ──approve (human)──►  pages/  ──►  ask / lint / eval
   raw docs            curator agent                  authoritative     agents + checks
```

## Quick start

```bash
pip install -r requirements.txt
python -m pytest -q                       # 13 tests, run fully offline

python -m wiki ask "What is the maximum grant?" --role viewer
python -m wiki ask "What percentage of projects are audited?" --role finance
python -m wiki lint                       # finds the planted deadline conflict
python -m wiki eval                       # hit@k, MRR, permission leaks

python -m wiki propose sources/2026-guideline-update-memo.md --owner jad
python -m wiki drafts
python -m wiki approve <slug> --reviewer jad
```

Without an API key everything runs offline: answers are extractive (best passage,
cited) and drafts are structured templates. With `ANTHROPIC_API_KEY` set, Claude
writes the answers and drafts (`WIKI_MODEL` picks the model).

## What each part does

| Part | File | Design choice |
|---|---|---|
| Pages | `wiki/store.py` | Markdown + YAML frontmatter: `status`, `access`, `owner`, `updated`, `sources`, `supersedes` / `superseded_by`, `reviewer`. Plain files, so Git gives version history for free. |
| Retrieval | `wiki/retrieve.py` | Heading-aware chunks + BM25. Permission filter runs *before* scoring, so a model never sees a page the user can't. Drafts and superseded pages are down-weighted. |
| Ask agent | `wiki/answer.py` | Numbered sources in the prompt, "cite every sentence", explicit `NOT_IN_WIKI` escape. Citations are checked after generation: invented or missing citations become warnings. |
| Curator agent | `wiki/curate.py` | Finds related pages, drafts a page with `[[links]]` and an "Open questions" section for anything that contradicts existing knowledge. Always lands in `drafts/`. |
| Review | `Wiki.approve` | Human gate: records reviewer and date, moves the page into `pages/`. |
| Lint | `wiki/lint.py` | Stale pages, reviewed pages without sources, broken links, bad supersede chains, and conflicting facts across *current* pages (superseded pages are allowed to differ). |
| Eval | `wiki/evaluate.py`, `eval/questions.yaml` | Retrieval hit@k and MRR per role, plus negative cases that fail if a role can reach a page it shouldn't. |

Current eval on the demo wiki: **8/8 answerable questions retrieved, MRR 0.92,
0 permission leaks.**

## What worked, what didn't (so far)

- **Permissions belong in retrieval, not in the prompt.** Telling a model "don't
  reveal finance pages" is not a control; filtering chunks before the model sees
  them is.
- **Superseded knowledge is the most common silent failure.** Old rate sheets look
  just as authoritative as new ones. Explicit `superseded_by` plus down-weighting
  fixed the ranking; the linter ignores expected differences between old and new.
- **Simple fact extraction catches real contradictions.** The planted
  "Application deadline" conflict (15 vs 31 March) is found by a regex over
  `Key: value` lines — no model needed. Fuzzier conflicts need an LLM pass.
- **Limitation: BM25 misses paraphrases.** "Can a university lead?" works; a
  question with no shared words would not. The retriever has a small interface so
  embeddings or a hybrid retriever can be swapped in.
- **Limitation: drafts are down-weighted on purpose,** so a brand-new memo only
  becomes the top answer once someone approves it. That is a deliberate trade-off
  of freshness for trust.

## Next steps

Hybrid retrieval (BM25 + embeddings), an LLM conflict check over related pages,
a source-freshness watcher that re-runs the curator when a source changes, and a
Microsoft Graph / SharePoint connector so pages can be drafted from where company
documents actually live.
