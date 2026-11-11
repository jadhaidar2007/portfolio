"""Command line: python -m wiki <command>

  ask "question" [--role viewer|employee|finance]
  propose sources/<file>.md [--owner name]
  drafts
  approve <slug> --reviewer name
  lint [--max-age-days N]
  eval
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import llm
from .answer import ask
from .curate import propose
from .evaluate import run_eval
from .lint import lint
from .retrieve import ROLE_ACCESS, BM25Retriever
from .store import Wiki

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wiki", description="AI-native knowledge base")
    parser.add_argument("--root", type=Path, default=ROOT, help="wiki folder")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ask = sub.add_parser("ask", help="answer a question with citations")
    p_ask.add_argument("question")
    p_ask.add_argument("--role", default="employee", choices=sorted(ROLE_ACCESS))

    p_prop = sub.add_parser("propose", help="draft a page from a source document")
    p_prop.add_argument("source", type=Path)
    p_prop.add_argument("--owner", default="unassigned")

    sub.add_parser("drafts", help="list drafts waiting for review")

    p_app = sub.add_parser("approve", help="promote a draft to a reviewed page")
    p_app.add_argument("slug")
    p_app.add_argument("--reviewer", required=True)

    p_lint = sub.add_parser("lint", help="find stale, conflicting or broken knowledge")
    p_lint.add_argument("--max-age-days", type=int, default=365)

    sub.add_parser("eval", help="retrieval quality and permission checks")

    args = parser.parse_args(argv)
    wiki = Wiki(args.root)

    if args.cmd == "ask":
        retriever = BM25Retriever(wiki.pages() + wiki.drafts())
        answer = ask(retriever, args.question, role=args.role)
        mode = "Claude" if answer.mode == "llm" else "offline (extractive)"
        print(f"[{mode}, role={args.role}]\n")
        print(answer.render())
    elif args.cmd == "propose":
        page = propose(wiki, args.source, owner=args.owner)
        print(f"Draft written: drafts/{page.slug}.md")
        print(f"Related pages: {', '.join(page.meta['related']) or 'none'}")
        print("Review it, then: python -m wiki approve", page.slug, "--reviewer <you>")
    elif args.cmd == "drafts":
        drafts = wiki.drafts()
        print("\n".join(f"{d.slug}  (owner: {d.meta.get('owner')})" for d in drafts) or "No drafts.")
    elif args.cmd == "approve":
        path = wiki.approve(args.slug, reviewer=args.reviewer)
        print(f"Approved -> {path.relative_to(args.root)}")
    elif args.cmd == "lint":
        issues = lint(wiki, max_age_days=args.max_age_days)
        print("\n".join(map(str, issues)) or "No issues.")
        return 1 if any(i.kind == "conflict" for i in issues) else 0
    elif args.cmd == "eval":
        print(run_eval(BM25Retriever(wiki.pages()), args.root / "eval" / "questions.yaml").render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
