"""Retrieval: heading-aware chunking + BM25, filtered by permissions.

Kept dependency-free on purpose: BM25 is transparent, fast, and good enough
for a few hundred pages. The Retriever interface is small so an embedding
or hybrid retriever can be dropped in later without touching the agents.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .store import Page

TOKEN_RE = re.compile(r"[a-z0-9€%]+(?:[.,][0-9]+)*")
STOPWORDS = set(
    "a an and are as at be by can do does for from has have how i in is it its of on or "
    "that the this to was what when where which who will with you your".split()
)

# Who may read what. Retrieval enforces this, so an agent can never quote
# a page the asking user is not allowed to see.
ROLE_ACCESS = {
    "viewer": {"public"},
    "employee": {"public", "internal"},
    "finance": {"public", "internal", "finance"},
}


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


@dataclass
class Chunk:
    page: Page
    heading: str
    text: str
    index: int

    @property
    def ref(self) -> str:
        return f"{self.page.slug}#{self.index}"


def chunk_page(page: Page, max_chars: int = 900) -> list[Chunk]:
    """Split on markdown headings, then on paragraphs if a section is long."""
    chunks: list[Chunk] = []
    heading = page.title
    buffer: list[str] = []

    def flush():
        text = "\n".join(buffer).strip()
        if text:
            chunks.append(Chunk(page, heading, text, len(chunks)))
        buffer.clear()

    for line in page.body.splitlines():
        if line.startswith("#"):
            flush()
            heading = line.lstrip("#").strip()
            continue
        buffer.append(line)
        if sum(len(b) for b in buffer) > max_chars and line.strip() == "":
            flush()
    flush()
    return chunks


@dataclass
class Hit:
    chunk: Chunk
    score: float


class BM25Retriever:
    def __init__(self, pages: list[Page], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.chunks = [c for p in pages for c in chunk_page(p)]
        self.docs = [tokenize(f"{c.page.title} {c.heading} {c.text}") for c in self.chunks]
        self.avgdl = sum(map(len, self.docs)) / max(len(self.docs), 1)
        df: Counter = Counter()
        for doc in self.docs:
            df.update(set(doc))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [Counter(doc) for doc in self.docs]

    def _score(self, query: list[str], i: int) -> float:
        tf, dl, score = self.tf[i], len(self.docs[i]), 0.0
        for term in query:
            if term not in tf:
                continue
            f = tf[term]
            score += self.idf[term] * f * (self.k1 + 1) / (
                f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            )
        return score

    def search(self, query: str, role: str = "employee", k: int = 4) -> list[Hit]:
        allowed = ROLE_ACCESS.get(role)
        if allowed is None:
            raise ValueError(f"Unknown role {role!r}. Use one of {sorted(ROLE_ACCESS)}")
        terms = tokenize(query)
        hits = []
        for i, chunk in enumerate(self.chunks):
            page = chunk.page
            if page.access not in allowed:
                continue
            score = self._score(terms, i)
            if score <= 0:
                continue
            # Prefer authoritative, current knowledge over drafts and superseded pages.
            if page.status != "reviewed":
                score *= 0.5
            if page.meta.get("superseded_by"):
                score *= 0.3
            hits.append(Hit(chunk, score))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]
