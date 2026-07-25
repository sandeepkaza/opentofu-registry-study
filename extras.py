"""Supporting numbers for the Paper 10 write-up (not in results.md aggregates).

Prints: absent-module exemplars by downloads, per-stratum download shares,
tofu-index freshness/target shape, and the tf-exclusive top-rule table.
Run: python extras.py
"""

import csv
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).parent / "data"
OFFICIAL = {"Azure", "aws-ia", "terraform-aws-modules", "GoogleCloudPlatform",
            "terraform-google-modules", "hashicorp", "oracle-terraform-modules"}


def load_tf():
    tf = {}
    for p in ("aws", "azurerm", "google"):
        for r in csv.DictReader(open(DATA / f"modules_tf_{p}.csv", encoding="utf-8")):
            tf[(r["namespace"], r["name"], p)] = r
    return tf


def load_det():
    return {(r["namespace"], r["name"], r["target"]): r
            for r in csv.DictReader(open(DATA / "tofu_details_matched.csv", encoding="utf-8"))}


tf, det = load_tf(), load_det()

absent, present = [], []
dl_by = defaultdict(lambda: [0, 0])  # stratum -> [present_dl, absent_dl]
for k, r in tf.items():
    d = det.get(k)
    if not d or d["exists_in_tofu"] == "ERROR":
        continue
    s = "official" if k[0] in OFFICIAL else "community"
    dl = int(r["downloads"] or 0)
    (present if d["exists_in_tofu"] == "True" else absent).append((dl, k, r))
    dl_by[s][0 if d["exists_in_tofu"] == "True" else 1] += dl

print("== totals ==")
print(f"comparable listings: {len(present)+len(absent)}  present {len(present)}  absent {len(absent)}")
for s, (p, a) in sorted(dl_by.items()):
    print(f"{s}: downloads present {p:,} absent {a:,} -> absent share {a/(p+a):.1%}")
tot_a = sum(v[1] for v in dl_by.values())
tot_p = sum(v[0] for v in dl_by.values())
print(f"all: absent download share {tot_a/(tot_a+tot_p):.1%}  (absent dl {tot_a:,})")

print("\n== top 15 absent-from-OpenTofu modules by TF downloads ==")
for dl, k, r in sorted(absent, reverse=True)[:15]:
    s = "official" if k[0] in OFFICIAL else "community"
    print(f"{dl:>12,}  {k[0]}/{k[1]}/{k[2]:<8} {s:<9} verified={r['verified']}")

print("\n== absent count by namespace (top 12) ==")
for ns, c in Counter(k[0] for _, k, _ in absent).most_common(12):
    print(f"{c:>4}  {ns}")

print("\n== median downloads: present vs absent ==")
print(f"present median {st.median([d for d, _, _ in present]):,.0f}  "
      f"absent median {st.median([d for d, _, _ in absent]):,.0f}")

print("\n== tofu-side popularity (stars) for matched modules ==")
pop = [int(d["popularity"]) for d in det.values() if (d.get("popularity") or "").isdigit()]
print(f"n={len(pop)} median stars {st.median(pop):.0f}")
blocked = [d for d in det.values() if d.get("is_blocked") == "True"]
print(f"is_blocked entries: {len(blocked)}")

print("\n== tf-exclusive scan: top rules by distinct repos ==")
rule_repos = defaultdict(set)
names = {}
for r in csv.DictReader(open(DATA / "scan_absent.csv", encoding="utf-8")):
    if r.get("check_id"):
        rule_repos[r["check_id"]].add(r["repo"])
        names[r["check_id"]] = r.get("check_name", "")
for cid, repos in sorted(rule_repos.items(), key=lambda kv: -len(kv[1]))[:12]:
    print(f"{len(repos):>4}  {cid:<16} {names[cid][:60]}")
