#!/usr/bin/env python3
"""
Normalize PR links from GitHub or Graphite to owner/repo/number coordinates.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from urllib.parse import urlparse


@dataclass
class PrTarget:
    source: str
    owner: str
    repo: str
    number: int

    @property
    def github_pr_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}/pull/{self.number}"

    @property
    def github_api_url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{self.number}"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["github_pr_url"] = self.github_pr_url
        payload["github_api_url"] = self.github_api_url
        return payload


SHORTCUT_PATTERN = re.compile(r"^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)#(?P<number>\d+)$")


def _clean_segments(path: str) -> list[str]:
    return [segment for segment in path.split("/") if segment]


def _parse_shortcut(value: str) -> PrTarget | None:
    match = SHORTCUT_PATTERN.match(value.strip())
    if not match:
        return None
    return PrTarget(
        source="shortcut",
        owner=match.group("owner"),
        repo=match.group("repo"),
        number=int(match.group("number")),
    )


def _parse_github(parsed) -> PrTarget:
    segments = _clean_segments(parsed.path)
    # Format: /<owner>/<repo>/pull/<number>
    if len(segments) < 4 or segments[2] != "pull" or not segments[3].isdigit():
        raise ValueError(
            "GitHub URL must match https://github.com/<owner>/<repo>/pull/<number>"
        )
    return PrTarget(
        source="github",
        owner=segments[0],
        repo=segments[1],
        number=int(segments[3]),
    )


def _parse_github_api(parsed) -> PrTarget:
    segments = _clean_segments(parsed.path)
    # Format: /repos/<owner>/<repo>/pulls/<number>
    if (
        len(segments) < 5
        or segments[0] != "repos"
        or segments[3] != "pulls"
        or not segments[4].isdigit()
    ):
        raise ValueError(
            "GitHub API URL must match https://api.github.com/repos/<owner>/<repo>/pulls/<number>"
        )
    return PrTarget(
        source="github-api",
        owner=segments[1],
        repo=segments[2],
        number=int(segments[4]),
    )


def _parse_graphite(parsed) -> PrTarget:
    segments = _clean_segments(parsed.path)
    # Format: /github/pr/<owner>/<repo>/<number>/<slug...>
    if (
        len(segments) < 6
        or segments[0] != "github"
        or segments[1] != "pr"
        or not segments[4].isdigit()
    ):
        raise ValueError(
            "Graphite URL must match https://app.graphite.com/github/pr/<owner>/<repo>/<number>/<slug>"
        )
    return PrTarget(
        source="graphite",
        owner=segments[2],
        repo=segments[3],
        number=int(segments[4]),
    )


def parse_pr_link(link: str) -> PrTarget:
    shortcut = _parse_shortcut(link)
    if shortcut:
        return shortcut

    raw = link.strip()
    if "://" not in raw and raw.startswith("github.com/"):
        raw = f"https://{raw}"
    if "://" not in raw and raw.startswith("app.graphite.com/"):
        raw = f"https://{raw}"

    parsed = urlparse(raw)
    host = parsed.netloc.lower()

    if host in {"github.com", "www.github.com"}:
        return _parse_github(parsed)
    if host == "api.github.com":
        return _parse_github_api(parsed)
    if host in {"app.graphite.com", "graphite.com", "www.graphite.com"}:
        return _parse_graphite(parsed)

    raise ValueError(
        f"Unsupported host '{parsed.netloc}'. Provide a GitHub PR URL, Graphite PR URL, or owner/repo#number."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr_link", help="GitHub or Graphite PR link")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    try:
        result = parse_pr_link(args.pr_link).to_dict()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
