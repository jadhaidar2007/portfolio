"""Wiki pages: markdown files with YAML frontmatter.

A page is the unit of authoritative knowledge. Frontmatter carries the
governance metadata that makes the wiki usable by both humans and agents:

    title, status (draft|reviewed), access (public|internal|finance),
    owner, updated, sources, supersedes / superseded_by, reviewer, reviewed_at
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
LINK_RE = re.compile(r"\[\[([a-z0-9\-]+)\]\]")

VALID_STATUS = {"draft", "reviewed"}
VALID_ACCESS = {"public", "internal", "finance"}


@dataclass
class Page:
    slug: str
    meta: dict
    body: str
    path: Path | None = None

    @property
    def title(self) -> str:
        return self.meta.get("title", self.slug)

    @property
    def status(self) -> str:
        return self.meta.get("status", "draft")

    @property
    def access(self) -> str:
        return self.meta.get("access", "internal")

    @property
    def updated(self) -> dt.date | None:
        value = self.meta.get("updated")
        if isinstance(value, dt.date):
            return value
        if isinstance(value, str):
            return dt.date.fromisoformat(value)
        return None

    @property
    def links(self) -> list[str]:
        return LINK_RE.findall(self.body)

    def to_markdown(self) -> str:
        front = yaml.safe_dump(self.meta, sort_keys=False, allow_unicode=True).strip()
        return f"---\n{front}\n---\n\n{self.body.strip()}\n"


def parse_page(text: str, slug: str, path: Path | None = None) -> Page:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return Page(slug=slug, meta={"title": slug, "status": "draft"}, body=text, path=path)
    meta = yaml.safe_load(match.group(1)) or {}
    return Page(slug=slug, meta=meta, body=match.group(2).strip(), path=path)


class Wiki:
    """A folder of pages. Drafts live in a separate folder until reviewed."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.pages_dir = self.root / "pages"
        self.drafts_dir = self.root / "drafts"
        self.sources_dir = self.root / "sources"

    def _load_dir(self, folder: Path) -> list[Page]:
        if not folder.exists():
            return []
        return [
            parse_page(p.read_text(encoding="utf-8"), p.stem, p)
            for p in sorted(folder.glob("*.md"))
        ]

    def pages(self) -> list[Page]:
        return self._load_dir(self.pages_dir)

    def drafts(self) -> list[Page]:
        return self._load_dir(self.drafts_dir)

    def get(self, slug: str) -> Page | None:
        for page in self.pages() + self.drafts():
            if page.slug == slug:
                return page
        return None

    def save_draft(self, page: Page) -> Path:
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        page.meta["status"] = "draft"
        path = self.drafts_dir / f"{page.slug}.md"
        path.write_text(page.to_markdown(), encoding="utf-8")
        page.path = path
        return path

    def approve(self, slug: str, reviewer: str, today: dt.date | None = None) -> Path:
        """Promote a draft to an authoritative page. A human is always in the loop."""
        draft_path = self.drafts_dir / f"{slug}.md"
        if not draft_path.exists():
            raise FileNotFoundError(f"No draft named {slug!r}")
        page = parse_page(draft_path.read_text(encoding="utf-8"), slug)
        today = today or dt.date.today()
        page.meta.update(
            status="reviewed",
            reviewer=reviewer,
            reviewed_at=today.isoformat(),
            updated=today.isoformat(),
        )
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        target = self.pages_dir / f"{slug}.md"
        target.write_text(page.to_markdown(), encoding="utf-8")
        draft_path.unlink()
        return target
