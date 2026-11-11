"""Curator agent: turns a raw source document into a *draft* wiki page.

Drafts never become authoritative on their own. A human reviews the diff
and runs `wiki approve`, which records who reviewed it and when.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from . import llm
from .retrieve import BM25Retriever
from .store import Page, Wiki, parse_page

SYSTEM = (
    "You maintain a company wiki. Given a new source document and related existing "
    "pages, write ONE wiki page in markdown (no frontmatter). Use short sections with "
    "## headings. Keep facts exactly as stated in the source. Link related pages as "
    "[[slug]]. End with a section '## Open questions' listing anything ambiguous or "
    "anything that contradicts the existing pages."
)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def _title_from(source_text: str, fallback: str) -> str:
    for line in source_text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if line.lower().startswith("subject:"):
            return line.split(":", 1)[1].strip()
    return fallback


def propose(wiki: Wiki, source_path: Path, owner: str = "unassigned") -> Page:
    source_text = Path(source_path).read_text(encoding="utf-8")
    title = _title_from(source_text, Path(source_path).stem)
    related = BM25Retriever(wiki.pages()).search(source_text[:2000], role="finance", k=3)
    related_slugs = sorted({h.chunk.page.slug for h in related})

    context = "\n\n".join(
        f"[[{h.chunk.page.slug}]] {h.chunk.page.title}:\n{h.chunk.text}" for h in related
    )
    body = llm.complete(
        SYSTEM,
        f"New source ({Path(source_path).name}):\n{source_text}\n\nRelated pages:\n{context}",
    )
    if body is None:  # offline: structured draft a human can finish
        body = (
            f"## Summary\n\n{source_text.strip()}\n\n"
            f"## Related pages\n\n" + "\n".join(f"- [[{s}]]" for s in related_slugs)
            + "\n\n## Open questions\n\n- Drafted offline: check wording and conflicts before approving."
        )

    page = Page(
        slug=slugify(title),
        meta={
            "title": title,
            "status": "draft",
            "access": "internal",
            "owner": owner,
            "updated": dt.date.today().isoformat(),
            "sources": [Path(source_path).name],
            "related": related_slugs,
        },
        body=body,
    )
    wiki.save_draft(page)
    return page
