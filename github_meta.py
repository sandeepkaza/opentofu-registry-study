"""Collect GitHub metadata for module source repos (Paper 4 pipeline step 2).

Usage:
    python github_meta.py --in modules_azurerm.csv modules_aws.csv modules_google.csv --out repos_meta.csv --tags-out repo_tags.csv

Auth: uses `gh auth token` (or GITHUB_TOKEN env var). Rate-limit aware, resumable:
re-running skips repos already present in --out.

Outputs
    repos_meta.csv : one row per unique repo (stars, forks, archived, pushed_at,
                     open_issues, contributor_count, release_count, ...)
    repo_tags.csv  : one row per tag per repo (tag name + commit date) — the raw
                     material for RQ1 semver/cadence analysis, done offline.
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests

API = "https://api.github.com"


def get_token() -> str:
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


SESSION = requests.Session()


def gh_get(url: str, **params):
    """GET with rate-limit handling. Returns Response or None on 404."""
    while True:
        r = SESSION.get(url, params=params, timeout=30)
        if r.status_code == 404:
            return None
        if r.status_code == 403 and r.headers.get("x-ratelimit-remaining") == "0":
            reset = int(r.headers.get("x-ratelimit-reset", time.time() + 60))
            wait = max(5, reset - time.time() + 2)
            print(f"  rate limit — sleeping {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r


def parse_repo(source: str) -> str | None:
    """'https://github.com/owner/repo' -> 'owner/repo'."""
    m = re.search(r"github\.com/([^/]+/[^/\s]+)", source or "")
    return m.group(1).removesuffix(".git") if m else None


def contributor_count(repo: str) -> int | None:
    # per_page=1 + Link header 'last' page number == contributor count (1 API call)
    r = gh_get(f"{API}/repos/{repo}/contributors", per_page=1, anon="true")
    if r is None:
        return None
    if "last" in (r.links or {}):
        m = re.search(r"[?&]page=(\d+)", r.links["last"]["url"])
        return int(m.group(1)) if m else None
    return len(r.json())


def all_tags(repo: str, max_pages: int = 10) -> list[dict]:
    tags = []
    url = f"{API}/repos/{repo}/tags"
    for _ in range(max_pages):
        r = gh_get(url, per_page=100)
        if r is None:
            break
        batch = r.json()
        tags.extend(batch)
        nxt = (r.links or {}).get("next")
        if not nxt:
            break
        url = nxt["url"]
    return tags


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inputs", nargs="+", required=True)
    ap.add_argument("--out", default="repos_meta.csv")
    ap.add_argument("--tags-out", default="repo_tags.csv")
    args = ap.parse_args()

    SESSION.headers.update({
        "Authorization": f"Bearer {get_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })

    # unique repos across all input CSVs, keep max downloads for context
    repos: dict[str, int] = {}
    for path in args.inputs:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                repo = parse_repo(row.get("source", ""))
                if repo:
                    dl = int(row.get("downloads") or 0)
                    repos[repo] = max(repos.get(repo, 0), dl)

    done = set()
    if os.path.exists(args.out):
        with open(args.out, newline="", encoding="utf-8") as f:
            done = {row["repo"] for row in csv.DictReader(f)}

    meta_fields = ["snapshot_utc", "repo", "registry_downloads", "stars", "forks",
                   "archived", "pushed_at", "created_at", "open_issues",
                   "contributor_count", "tag_count", "license", "not_found"]
    tag_fields = ["repo", "tag", "sha"]

    meta_new = not os.path.exists(args.out)
    tags_new = not os.path.exists(args.tags_out)
    with open(args.out, "a", newline="", encoding="utf-8") as mf, \
         open(args.tags_out, "a", newline="", encoding="utf-8") as tf:
        mw = csv.DictWriter(mf, fieldnames=meta_fields)
        tw = csv.DictWriter(tf, fieldnames=tag_fields)
        if meta_new:
            mw.writeheader()
        if tags_new:
            tw.writeheader()

        todo = [r for r in sorted(repos, key=repos.get, reverse=True) if r not in done]
        print(f"{len(repos)} unique repos, {len(done)} done, {len(todo)} to fetch",
              file=sys.stderr)

        for i, repo in enumerate(todo, 1):
            snapshot = datetime.now(timezone.utc).isoformat(timespec="seconds")
            r = gh_get(f"{API}/repos/{repo}")
            if r is None:
                mw.writerow({"snapshot_utc": snapshot, "repo": repo,
                             "registry_downloads": repos[repo], "not_found": True})
                mf.flush()
                continue
            j = r.json()
            tags = all_tags(repo)
            for t in tags:
                tw.writerow({"repo": repo, "tag": t.get("name"),
                             "sha": (t.get("commit") or {}).get("sha")})
            mw.writerow({
                "snapshot_utc": snapshot,
                "repo": repo,
                "registry_downloads": repos[repo],
                "stars": j.get("stargazers_count"),
                "forks": j.get("forks_count"),
                "archived": j.get("archived"),
                "pushed_at": j.get("pushed_at"),
                "created_at": j.get("created_at"),
                "open_issues": j.get("open_issues_count"),
                "contributor_count": contributor_count(repo),
                "tag_count": len(tags),
                "license": (j.get("license") or {}).get("spdx_id"),
                "not_found": False,
            })
            mf.flush()
            tf.flush()
            if i % 25 == 0:
                print(f"  {i}/{len(todo)} repos done", file=sys.stderr)

    print(f"Done -> {args.out}, {args.tags_out}", file=sys.stderr)
    # ponytail: issue-response latency (RQ3) deferred — needs per-issue timeline
    # calls (~30x API cost); add sampled version once core dataset is validated.


if __name__ == "__main__":
    main()
