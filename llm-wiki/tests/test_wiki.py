import datetime as dt
import shutil
from pathlib import Path

import pytest

from wiki.answer import ask, check_citations
from wiki.curate import propose
from wiki.evaluate import run_eval
from wiki.lint import extract_facts, lint
from wiki.retrieve import BM25Retriever
from wiki.store import Wiki

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def wiki(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # tests run offline
    for folder in ("pages", "sources", "eval"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    return Wiki(tmp_path)


def test_retrieval_finds_right_page(wiki):
    hits = BM25Retriever(wiki.pages()).search("maximum grant amount", role="viewer")
    assert hits[0].chunk.page.slug == "eligibility"


def test_superseded_page_ranks_below_current(wiki):
    hits = BM25Retriever(wiki.pages()).search("maximum grant", role="employee", k=20)
    slugs = [h.chunk.page.slug for h in hits]
    assert slugs.index("eligibility") < slugs.index("funding-rates-2025")


def test_permissions_are_enforced(wiki):
    retriever = BM25Retriever(wiki.pages())
    for role in ("viewer", "employee"):
        assert all(h.chunk.page.access != "finance"
                   for h in retriever.search("audit sample rate", role=role, k=10))
    assert any(h.chunk.page.slug == "audit-checklist"
               for h in retriever.search("audit sample rate", role="finance"))


def test_unknown_role_rejected(wiki):
    with pytest.raises(ValueError):
        BM25Retriever(wiki.pages()).search("anything", role="admin")


def test_offline_answer_is_cited(wiki):
    answer = ask(BM25Retriever(wiki.pages()), "Can universities lead a project?", role="viewer")
    assert answer.mode == "extractive"
    assert "[1]" in answer.text
    assert answer.sources[0].chunk.page.slug == "eligibility"


def test_no_access_means_no_answer(wiki):
    answer = ask(BM25Retriever(wiki.pages()), "audit repayment interest", role="viewer")
    assert all(h.chunk.page.access == "public" for h in answer.sources)


def test_citation_checker():
    assert check_citations("Grant is €150,000 [1].", 2) == []
    assert "do not exist" in check_citations("See [5].", 2)[0]
    assert "no citations" in check_citations("Trust me.", 2)[0]


def test_lint_finds_planted_conflict(wiki):
    issues = lint(wiki, today=dt.date(2026, 11, 11))
    conflicts = [i for i in issues if i.kind == "conflict"]
    assert len(conflicts) == 1
    assert "application deadline" in conflicts[0].message


def test_lint_ignores_superseded_values(wiki):
    issues = lint(wiki, today=dt.date(2026, 11, 11))
    assert not any("maximum grant" in i.message for i in issues)


def test_lint_flags_stale(wiki):
    issues = lint(wiki, today=dt.date(2028, 1, 1))
    assert any(i.kind == "stale" for i in issues)


def test_fact_extraction(wiki):
    facts = extract_facts(wiki.get("eligibility"))
    assert facts["maximum grant"] == "€150,000"


def test_propose_then_approve(wiki):
    page = propose(wiki, wiki.sources_dir / "2026-guideline-update-memo.md", owner="jad")
    assert page.status == "draft"
    assert (wiki.drafts_dir / f"{page.slug}.md").exists()
    assert any(i.kind == "pending-draft" for i in lint(wiki))

    wiki.approve(page.slug, reviewer="jad", today=dt.date(2026, 11, 11))
    approved = wiki.get(page.slug)
    assert approved.status == "reviewed"
    assert approved.meta["reviewer"] == "jad"
    assert not wiki.drafts()


def test_eval_has_no_misses_or_leaks(wiki):
    result = run_eval(BM25Retriever(wiki.pages()), wiki.root / "eval" / "questions.yaml")
    assert result.leaks == []
    assert result.misses == []
