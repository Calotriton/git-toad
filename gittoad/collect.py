"""Collect public GitHub activity into a snapshot the renderer can read."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://api.github.com/graphql"

PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    createdAt
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes { primaryLanguage { name color } }
    }
    repositoriesContributedTo(first: 100, includeUserRepositories: false,
                              contributionTypes: [COMMIT, PULL_REQUEST, PULL_REQUEST_REVIEW]) {
      nodes { isPrivate primaryLanguage { name color } }
    }
  }
}
"""

CALENDAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


class CollectError(RuntimeError):
    pass


def find_token() -> str:
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    raise CollectError("set GITHUB_TOKEN or GH_TOKEN (any token works; only public data is read)")


def graphql(query: str, variables: dict, token: str) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "git-toad"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as err:
        raise CollectError(f"GitHub API returned {err.code}: {err.read().decode(errors='replace')[:300]}") from err
    if data.get("errors"):
        raise CollectError("GitHub API error: " + "; ".join(e.get("message", "?") for e in data["errors"]))
    return data["data"]


def collect(login: str, token: str | None = None) -> dict:
    token = token or find_token()
    profile = graphql(PROFILE_QUERY, {"login": login}, token).get("user")
    if not profile:
        raise CollectError(f"user {login!r} not found")

    languages: dict[str, dict] = {}
    repos = profile["repositories"]["nodes"] + [
        r for r in profile["repositoriesContributedTo"]["nodes"] if not r.get("isPrivate")
    ]
    for repo in repos:
        lang = repo.get("primaryLanguage")
        if lang and lang.get("color"):
            entry = languages.setdefault(lang["name"], {"name": lang["name"], "color": lang["color"], "repos": 0})
            entry["repos"] += 1

    created = datetime.fromisoformat(profile["createdAt"].replace("Z", "+00:00")).date()
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    days: dict[str, int] = {}
    start = created
    while start <= yesterday:
        end = min(start + timedelta(days=364), yesterday)
        data = graphql(
            CALENDAR_QUERY,
            {"login": login, "from": f"{start.isoformat()}T00:00:00Z", "to": f"{end.isoformat()}T23:59:59Z"},
            token,
        )
        for week in data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                d = date.fromisoformat(day["date"])
                if start <= d <= end:
                    days[day["date"]] = day["contributionCount"]
        start = end + timedelta(days=1)

    return {
        "login": profile["login"],
        "created_at": created.isoformat(),
        "observed": yesterday.isoformat(),
        "languages": sorted(languages.values(), key=lambda l: (-l["repos"], l["name"])),
        "days": sorted(days.items()),
    }
