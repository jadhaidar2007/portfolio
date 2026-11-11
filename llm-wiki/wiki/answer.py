"""Ask agent: answers only from retrieved pages, with numbered citations.

Guardrails:
  * the model only sees chunks the user's role may read,
  * every claim must cite a source like [2],
  * citations are checked after generation; uncited or invented citations
    are reported instead of silently trusted,
  * if nothing relevant is retrieved, the agent says so instead of guessing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import llm
from .retrieve import BM25Retriever, Hit

CITE_RE = re.compile(r"\[(\d+)\]")

SYSTEM = (
    "You answer questions using ONLY the numbered sources provided. "
    "Cite every factual sentence with its source number in square brackets, e.g. [2]. "
    "If sources disagree, say so and prefer the most recently updated reviewed source. "
    "If the sources do not contain the answer, reply exactly: NOT_IN_WIKI"
)


@dataclass
class Answer:
    text: str
    sources: list[Hit]
    warnings: list[str] = field(default_factory=list)
    mode: str = "llm"

    def render(self) -> str:
        lines = [self.text, "", "Sources:"]
        for i, hit in enumerate(self.sources, 1):
            p = hit.chunk.page
            flag = "" if p.status == "reviewed" else f" ({p.status})"
            if p.meta.get("superseded_by"):
                flag += f" (superseded by {p.meta['superseded_by']})"
            lines.append(f"  [{i}] {p.title} › {hit.chunk.heading} — {hit.chunk.ref}{flag}")
        for w in self.warnings:
            lines.append(f"  ! {w}")
        return "\n".join(lines)


def format_sources(hits: list[Hit]) -> str:
    blocks = []
    for i, hit in enumerate(hits, 1):
        p = hit.chunk.page
        blocks.append(
            f"[{i}] {p.title} › {hit.chunk.heading} "
            f"(status: {p.status}, updated: {p.meta.get('updated')}, "
            f"superseded_by: {p.meta.get('superseded_by', 'none')})\n{hit.chunk.text}"
        )
    return "\n\n".join(blocks)


def check_citations(text: str, n_sources: int) -> list[str]:
    warnings = []
    cited = {int(n) for n in CITE_RE.findall(text)}
    invalid = sorted(c for c in cited if c < 1 or c > n_sources)
    if invalid:
        warnings.append(f"Answer cites sources that do not exist: {invalid}")
    if not cited:
        warnings.append("Answer contains no citations; treat it as unverified.")
    return warnings


def extractive_answer(hits: list[Hit]) -> str:
    """Offline fallback: return the best passage verbatim, cited."""
    best = hits[0].chunk
    first_para = best.text.strip().split("\n\n")[0]
    return f"{first_para} [1]"


def ask(retriever: BM25Retriever, question: str, role: str = "employee", k: int = 4) -> Answer:
    hits = retriever.search(question, role=role, k=k)
    if not hits:
        return Answer("I could not find this in the pages you have access to.", [], mode="none")

    prompt = f"Sources:\n\n{format_sources(hits)}\n\nQuestion: {question}"
    text = llm.complete(SYSTEM, prompt)
    if text is None:
        return Answer(extractive_answer(hits), hits, mode="extractive")
    if text.strip() == "NOT_IN_WIKI":
        return Answer("The wiki does not answer this yet.", hits, mode="llm")
    return Answer(text.strip(), hits, check_citations(text, len(hits)), mode="llm")
