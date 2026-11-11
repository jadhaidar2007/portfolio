"""Retrieval evaluation: is the right page retrieved, for the right people?

Each case: question, role, expected page slug (or null when the role must
NOT be able to reach the answer). Reports hit@k, MRR and permission leaks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .retrieve import BM25Retriever


@dataclass
class EvalResult:
    total: int
    hits: int
    mrr: float
    leaks: list[str]
    misses: list[str]

    def render(self) -> str:
        lines = [
            f"cases: {self.total}",
            f"hit@k: {self.hits}/{self.total - self._negatives} answerable questions",
            f"permission checks: {self._negatives}",
            f"MRR:   {self.mrr:.2f}",
            f"permission leaks: {len(self.leaks)}",
        ]
        lines += [f"  MISS  {m}" for m in self.misses]
        lines += [f"  LEAK  {l}" for l in self.leaks]
        return "\n".join(lines)

    _negatives: int = 0


def run_eval(retriever: BM25Retriever, cases_path: Path, k: int = 3) -> EvalResult:
    cases = yaml.safe_load(Path(cases_path).read_text(encoding="utf-8"))
    hits, rr, leaks, misses, negatives = 0, 0.0, [], [], 0
    for case in cases:
        results = retriever.search(case["question"], role=case.get("role", "employee"), k=k)
        slugs = [h.chunk.page.slug for h in results]
        expected = case.get("expected")
        forbidden = case.get("forbidden")
        if forbidden:
            negatives += 1
            if forbidden in slugs:
                leaks.append(f"{case['question']!r} as {case['role']} reached {forbidden}")
            continue
        if expected in slugs:
            hits += 1
            rr += 1 / (slugs.index(expected) + 1)
        else:
            misses.append(f"{case['question']!r} -> got {slugs}, expected {expected}")
    answerable = len(cases) - negatives
    result = EvalResult(len(cases), hits, rr / max(answerable, 1), leaks, misses)
    result._negatives = negatives
    return result
