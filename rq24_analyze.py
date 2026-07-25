"""Paper 10 RQ2 + RQ4 analysis.

RQ2: governance delta — repos backing modules present in OpenTofu ("shared")
     vs repos whose top-500 modules are all absent ("tf-exclusive").
RQ4: checkov security-default shape of the tf-exclusive top-100 scan
     (data/scan_absent.csv) vs Paper 4's top-100 baseline re-sliced by presence.

Run: python rq24_analyze.py   (from paper10 folder)
"""

import csv
import re
import statistics as st
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
P4 = HERE.parent / "paper4-terraform-registry"
SNAPSHOT = datetime(2026, 7, 18, tzinfo=timezone.utc)  # dual-registry snapshot date


def repo_of(source):
    m = re.search(r"github\.com/([^/]+/[^/\s]+)", source or "")
    return m.group(1).removesuffix(".git") if m else None


def load_presence():
    """(namespace, name, provider) -> exists_in_tofu bool."""
    pres = {}
    with open(DATA / "tofu_details_matched.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["exists_in_tofu"] in ("True", "False"):
                pres[(row["namespace"], row["name"], row["target"])] = row["exists_in_tofu"] == "True"
    return pres


def load_modules():
    rows = []
    for p in ["aws", "azurerm", "google"]:
        with open(DATA / f"modules_tf_{p}.csv", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
    return rows


def rq2():
    pres = load_presence()
    mods = load_modules()

    # repo -> shared if ANY of its top-500 modules is present in tofu
    repo_pop, repo_verified = {}, defaultdict(bool)
    for m in mods:
        repo = repo_of(m["source"])
        if not repo:
            continue
        key = (m["namespace"], m["name"], m["provider"])
        if key not in pres:
            continue
        if pres[key]:
            repo_pop[repo] = "shared"
        else:
            repo_pop.setdefault(repo, "tf-exclusive")
        repo_verified[repo] |= m["verified"].lower() == "true"

    meta = {}
    with open(DATA / "repos_meta.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            meta[row["repo"]] = row

    print("## RQ2 — governance: shared vs tf-exclusive repo populations\n")
    for pop in ["shared", "tf-exclusive"]:
        repos = [r for r, p in repo_pop.items() if p == pop]
        rows = [meta[r] for r in repos if r in meta]
        missing = len(repos) - len(rows)
        found = [r for r in rows if r["not_found"] != "True"]
        gone = [r for r in rows if r["not_found"] == "True"]

        def nums(field):
            return [int(r[field]) for r in found if (r[field] or "").isdigit()]

        archived = [r for r in found if r["archived"] == "True"]
        dormant = []
        for r in found:
            if r["pushed_at"]:
                pushed = datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
                if (SNAPSHOT - pushed).days > 365:
                    dormant.append(r)
        contrib = nums("contributor_count")
        stars = nums("stars")
        verified = [r for r in repos if repo_verified[r]]
        print(f"### {pop}")
        print(f"- repos: {len(repos)} (meta rows {len(rows)}, no meta {missing})")
        print(f"- source repo deleted/404: {len(gone)} ({len(gone)/max(len(rows),1)*100:.1f}%)")
        print(f"- archived: {len(archived)} ({len(archived)/max(len(found),1)*100:.1f}%)")
        print(f"- dormant >1y (pushed_at before {SNAPSHOT.date()} - 365d): "
              f"{len(dormant)} ({len(dormant)/max(len(found),1)*100:.1f}%)")
        print(f"- median contributors: {st.median(contrib) if contrib else 'n/a'}"
              f"  | bus factor ==1 contributor: {sum(1 for c in contrib if c == 1)}"
              f" ({sum(1 for c in contrib if c == 1)/max(len(contrib),1)*100:.1f}%)")
        print(f"- median stars: {st.median(stars) if stars else 'n/a'}")
        print(f"- official/verified-backed repos: {len(verified)} ({len(verified)/max(len(repos),1)*100:.1f}%)")
        print()


def summarize_scan(rows, label):
    """rows: per-repo dict repo -> (passed, failed, [check_ids]) from scan CSV rows."""
    per_repo = {}
    for r in rows:
        repo = r["repo"]
        if r["failed"] in ("clone_error", "scan_error"):
            per_repo.setdefault(repo, {"err": True})
            continue
        d = per_repo.setdefault(repo, {"err": False, "passed": int(r["passed"] or 0),
                                       "failed": int(r["failed"] or 0), "checks": set()})
        if r["check_id"]:
            d["checks"].add(r["check_id"])
    ok = {k: v for k, v in per_repo.items() if not v.get("err")}
    scannable = {k: v for k, v in ok.items() if v["passed"] + v["failed"] > 0}
    failing = {k: v for k, v in scannable.items() if v["failed"] > 0}
    print(f"### {label}")
    print(f"- repos scanned: {len(per_repo)} (errors {len(per_repo)-len(ok)}, "
          f"no terraform checks applicable: {len(ok)-len(scannable)})")
    if scannable:
        print(f"- repos with >=1 failed check: {len(failing)} "
              f"({len(failing)/len(scannable)*100:.1f}% of scannable)")
        print(f"- median failed per repo: {st.median([v['failed'] for v in scannable.values()])}")
        print(f"- median passed per repo: {st.median([v['passed'] for v in scannable.values()])}")
    rule_repos = Counter()
    for v in scannable.values():
        for c in v["checks"]:
            rule_repos[c] += 1
    print(f"- top 10 rules by distinct repos: {rule_repos.most_common(10)}")
    print()


def rq4():
    pres = load_presence()

    def mod_key(module_id):
        parts = (module_id or "").split("/")
        return tuple(parts[:3]) if len(parts) >= 3 else None

    print("## RQ4 — checkov security defaults\n")

    with open(DATA / "scan_absent.csv", encoding="utf-8") as f:
        summarize_scan(list(csv.DictReader(f)), "tf-exclusive top-100/provider (fresh scan, checkov 3.3.8)")

    # Paper 4 baseline re-sliced by presence
    p4_rows = []
    for p in ["aws", "azurerm", "google"]:
        with open(P4 / f"scan_{p}.csv", encoding="utf-8") as f:
            p4_rows.extend(csv.DictReader(f))
    shared = [r for r in p4_rows if pres.get(mod_key(r["module_id"])) is True]
    excl = [r for r in p4_rows if pres.get(mod_key(r["module_id"])) is False]
    unk = [r for r in p4_rows if pres.get(mod_key(r["module_id"])) is None]
    summarize_scan(shared, "Paper 4 top-100 baseline, present-in-tofu slice")
    summarize_scan(excl, "Paper 4 top-100 baseline, absent-from-tofu slice")
    print(f"(P4 rows with no presence data — module not in P10 top-500 snapshot: "
          f"{len({r['repo'] for r in unk})} repos)\n")


if __name__ == "__main__":
    rq2()
    rq4()
