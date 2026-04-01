"""Fetch .quiz.md files from GitHub repos or raw URLs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

_RAW_BASE = "https://raw.githubusercontent.com"
_API_BASE = "https://api.github.com"

# Patterns: owner/repo, owner/repo/blob/branch/path, full github.com URLs
_SHORTHAND_RE = re.compile(
    r"^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)$"
)
_BLOB_RE = re.compile(
    r"^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)"
    r"/blob/(?P<ref>[^/]+)/(?P<path>.+)$"
)


@dataclass
class QuizSource:
    owner: str
    repo: str
    ref: str
    path: str  # empty for repo-level (list all quiz files)

    @property
    def display_name(self) -> str:
        if self.path:
            return f"{self.owner}/{self.repo}/{self.path}"
        return f"{self.owner}/{self.repo}"


def parse_source(raw: str) -> QuizSource:
    """Parse a GitHub URL or shorthand into a QuizSource."""
    raw = raw.strip().rstrip("/")

    # Full URL
    if raw.startswith("http://") or raw.startswith("https://"):
        u = urlparse(raw)
        parts = u.path.strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub URL: {raw}")
        owner, repo = parts[0], parts[1].removesuffix(".git")
        if len(parts) >= 5 and parts[2] == "blob":
            ref = parts[3]
            path = "/".join(parts[4:])
            return QuizSource(owner, repo, ref, path)
        if len(parts) >= 5 and parts[2] == "tree":
            ref = parts[3]
            path = "/".join(parts[4:])
            return QuizSource(owner, repo, ref, path)
        return QuizSource(owner, repo, "HEAD", "")

    # owner/repo/blob/ref/path
    m = _BLOB_RE.match(raw)
    if m:
        return QuizSource(m["owner"], m["repo"], m["ref"], m["path"])

    # owner/repo
    m = _SHORTHAND_RE.match(raw)
    if m:
        return QuizSource(m["owner"], m["repo"], "HEAD", "")

    # owner/repo/path (subpath shorthand)
    parts = raw.split("/", 2)
    if len(parts) >= 3 and all(parts):
        owner, repo = parts[0], parts[1]
        path = parts[2]
        return QuizSource(owner, repo, "HEAD", path)

    raise ValueError(
        f"Cannot parse source: {raw!r}. "
        "Use owner/repo, owner/repo/folder, a GitHub URL, or a .quiz.md path."
    )


async def fetch_file(client: httpx.AsyncClient, source: QuizSource) -> str:
    """Fetch a single .quiz.md file content."""
    url = f"{_RAW_BASE}/{source.owner}/{source.repo}/{source.ref}/{source.path}"
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.text


@dataclass
class RepoFile:
    path: str
    name: str


async def list_quiz_files(
    client: httpx.AsyncClient, source: QuizSource
) -> list[RepoFile]:
    """List .quiz.md files in a repo (recursively via the Git tree API)."""
    # Resolve HEAD to default branch
    ref = source.ref
    if ref == "HEAD":
        repo_resp = await client.get(
            f"{_API_BASE}/repos/{source.owner}/{source.repo}"
        )
        repo_resp.raise_for_status()
        ref = repo_resp.json()["default_branch"]

    url = f"{_API_BASE}/repos/{source.owner}/{source.repo}/git/trees/{ref}?recursive=1"
    resp = await client.get(url)
    resp.raise_for_status()
    tree = resp.json().get("tree", [])

    # Filter by source.path prefix when pointing to a folder
    prefix = source.path.rstrip("/") + "/" if source.path and not source.path.endswith(".quiz.md") else ""

    files: list[RepoFile] = []
    for item in tree:
        if item["type"] == "blob" and item["path"].endswith(".quiz.md"):
            if prefix and not item["path"].startswith(prefix):
                continue
            name = item["path"].rsplit("/", 1)[-1]
            files.append(RepoFile(path=item["path"], name=name))
    files.sort(key=lambda f: f.path)
    return files
