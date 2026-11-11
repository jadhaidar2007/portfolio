"""Wiki linter: finds the failure modes that make a knowledge base untrustworthy.

Checks
  stale            reviewed page not updated within max_age_days
  no-sources       reviewed page that cites no source document
  broken-link      [[slug]] pointing to a page that does not exist
  bad-supersede    superseded_by / supersedes pointing nowhere
  conflict         the same fact key with different values on two current pages
  pending-draft    drafts waiting for human review

Fact extraction is deliberately simple: lines like "- **Maximum grant:** €150,000"
or "Application deadline: 31 March 2027". Simple rules catch real contradictions
cheaply; an LLM pass can be layered on top for fuzzier conflicts.
"""
from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from dataclasses import dataclass

from .store import Page, Wiki

FACT_RE = re.compile(r"^\s*[-*]?\s*\**([A-Z][A-Za-z ()/-]{2,40}?)\**\s*:\s*\**\s*(.+?)\s*$")


@dataclass
class Issue:
    kind: str
    slug: str
    message: str

    def __str__(self) -> str:
        return f"{self.kind:<14} {self.slug:<28} {self.message}"


def extract_facts(page: Page) -> dict[str, str]:
    facts = {}
    for line in page.body.splitlines():
        m = FACT_RE.match(line)
        if m:
            key = m.group(1).strip().lower()
            value = m.group(2).strip().rstrip(".").replace("*", "")
            facts[key] = value
    return facts


def lint(wiki: Wiki, today: dt.date | None = None, max_age_days: int = 365) -> list[Issue]:
    today = today or dt.date.today()
    pages = wiki.pages()
    slugs = {p.slug for p in pages} | {d.slug for d in wiki.drafts()}
    issues: list[Issue] = []

    for p in pages:
        if p.updated and (today - p.updated).days > max_age_days and not p.meta.get("superseded_by"):
            issues.append(Issue("stale", p.slug, f"last updated {p.updated} ({(today - p.updated).days} days ago)"))
        if p.status == "reviewed" and not p.meta.get("sources"):
            issues.append(Issue("no-sources", p.slug, "reviewed page has no source documents"))
        for link in p.links:
            if link not in slugs:
                issues.append(Issue("broken-link", p.slug, f"links to missing page [[{link}]]"))
        for field in ("superseded_by", "supersedes"):
            target = p.meta.get(field)
            if target and target not in slugs:
                issues.append(Issue("bad-supersede", p.slug, f"{field} -> {target} does not exist"))

    # Conflicts only among *current* pages: superseded pages are expected to differ.
    seen: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for p in pages:
        if p.meta.get("superseded_by"):
            continue
        for key, value in extract_facts(p).items():
            seen[key].append((p.slug, value))
    for key, entries in seen.items():
        values = {v for _, v in entries}
        if len(values) > 1:
            detail = "; ".join(f"{s}: {v}" for s, v in entries)
            issues.append(Issue("conflict", entries[0][0], f"'{key}' differs -> {detail}"))

    for d in wiki.drafts():
        issues.append(Issue("pending-draft", d.slug, "waiting for human review (wiki approve)"))

    return issues
