"""Paper 10 figures (vector PDF, IEEE single-column width 3.5in).

Fig 1 (fig_presence.pdf): presence of Terraform top-500 modules in the OpenTofu
      registry, by provider and by governance stratum — carries the inversion
      (official absent 62.8% vs community 25.4%) plus the download-weighted bar.
Fig 2 (fig_governance.pdf): maintenance-health metrics, shared vs tf-exclusive
      repository populations — the "not abandonware" result.
Fig 3 (fig_rules.pdf): top failed checkov rules, tf-exclusive population vs the
      Paper 4 present-in-tofu baseline — the registry-invariance result.

Run: python make_figures.py   (from the paper10 folder)
"""

import csv
import statistics as st
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
DATA = HERE / "data"
P4 = HERE.parent / "paper4-terraform-registry"
SNAPSHOT = datetime(2026, 7, 18, tzinfo=timezone.utc)

OFFICIAL = {"Azure", "aws-ia", "terraform-aws-modules", "GoogleCloudPlatform",
            "terraform-google-modules", "hashicorp", "oracle-terraform-modules"}

# Okabe-Ito: blue = present/shared, vermillion = absent/tf-exclusive.
BLUE, VERM = "#0072B2", "#D55E00"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d9d8d3"

plt.rcParams.update({
    "font.size": 7.5, "axes.labelsize": 7.5, "axes.titlesize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "font.family": "serif", "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.labelcolor": INK, "pdf.fonttype": 42,
})


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def repo_of(source):
    import re
    m = __import__("re").search(r"github\.com/([^/]+/[^/\s]+)", source or "")
    return m.group(1).removesuffix(".git") if m else None


def load_presence():
    return {(r["namespace"], r["name"], r["target"]): r["exists_in_tofu"]
            for r in load(DATA / "tofu_details_matched.csv")}


def load_modules():
    rows = []
    for p in ("aws", "azurerm", "google"):
        for r in load(DATA / f"modules_tf_{p}.csv"):
            r["_provider"] = p
            rows.append(r)
    return rows


pres = load_presence()
mods = load_modules()

# ---------- Fig 1: presence ----------
groups = ["aws", "azurerm", "google", "official", "community", "by\ndownloads"]
present = Counter()
absent = Counter()
dl_p = dl_a = 0
for m in mods:
    e = pres.get((m["namespace"], m["name"], m["_provider"]))
    if e not in ("True", "False"):
        continue
    ok = e == "True"
    strat = "official" if m["namespace"] in OFFICIAL else "community"
    for g in (m["_provider"], strat):
        (present if ok else absent)[g] += 1
    dl = int(m["downloads"] or 0)
    if ok:
        dl_p += dl
    else:
        dl_a += dl

pct_p, pct_a, ns = [], [], []
for g in groups[:5]:
    tot = present[g] + absent[g]
    pct_p.append(100 * present[g] / tot)
    pct_a.append(100 * absent[g] / tot)
    ns.append(tot)
pct_p.append(100 * dl_p / (dl_p + dl_a))
pct_a.append(100 * dl_a / (dl_p + dl_a))
ns.append(None)

fig, ax = plt.subplots(figsize=(3.5, 2.3))
x = range(len(groups))
ax.bar(x, pct_p, 0.62, color=BLUE, label="present in OpenTofu")
ax.bar(x, pct_a, 0.62, bottom=pct_p, color=VERM, hatch="///",
       edgecolor="white", linewidth=0.3, label="absent")
for i, (a, n) in enumerate(zip(pct_a, ns)):
    ax.annotate(f"{a:.1f}", (i, 100.8), ha="center", fontsize=6.5, color=VERM)
    if n:
        ax.annotate(f"n={n}", (i, 2), ha="center", fontsize=6, color="white")
ax.axvline(2.5, color=MUTED, linewidth=0.5, linestyle=":")
ax.axvline(4.5, color=MUTED, linewidth=0.5, linestyle=":")
ax.set_xticks(list(x), groups)
ax.set_ylabel("Share of Terraform top-500 listings (%)")
ax.set_ylim(0, 108)
ax.spines[["top", "right"]].set_visible(False)
ax.yaxis.grid(True, linewidth=0.3, color=GRID)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.42))
fig.tight_layout()
fig.savefig("fig_presence.pdf")
print("fig_presence.pdf")

# ---------- Fig 2: governance ----------
repo_pop, repo_verified = {}, defaultdict(bool)
for m in mods:
    repo = repo_of(m["source"])
    e = pres.get((m["namespace"], m["name"], m["_provider"]))
    if not repo or e not in ("True", "False"):
        continue
    if e == "True":
        repo_pop[repo] = "shared"
    else:
        repo_pop.setdefault(repo, "tf-exclusive")
    repo_verified[repo] |= m["verified"].lower() == "true"

meta = {r["repo"]: r for r in load(DATA / "repos_meta.csv")}
metrics = ["vendor-\nbacked", "archived", "dormant\n>1y", "bus\nfactor 1", "source\n404"]
vals = {}
for pop in ("shared", "tf-exclusive"):
    repos = [r for r, p in repo_pop.items() if p == pop]
    rows = [meta[r] for r in repos if r in meta]
    found = [r for r in rows if r["not_found"] != "True"]
    gone = [r for r in rows if r["not_found"] == "True"]
    contrib = [int(r["contributor_count"]) for r in found
               if (r["contributor_count"] or "").isdigit()]
    dormant = [r for r in found if r["pushed_at"] and
               (SNAPSHOT - datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))).days > 365]
    vals[pop] = [
        100 * sum(1 for r in repos if repo_verified[r]) / len(repos),
        100 * sum(1 for r in found if r["archived"] == "True") / len(found),
        100 * len(dormant) / len(found),
        100 * sum(1 for c in contrib if c == 1) / len(contrib),
        100 * len(gone) / len(rows),
    ]
    vals[pop + "_n"] = len(repos)

fig, ax = plt.subplots(figsize=(3.5, 2.15))
x = range(len(metrics))
w = 0.38
b1 = ax.bar([i - w / 2 for i in x], vals["shared"], w, color=BLUE,
            label=f"shared (n={vals['shared_n']})")
b2 = ax.bar([i + w / 2 for i in x], vals["tf-exclusive"], w, color=VERM, hatch="///",
            edgecolor="white", linewidth=0.3,
            label=f"tf-exclusive (n={vals['tf-exclusive_n']})")
for bars in (b1, b2):
    for rect in bars:
        ax.annotate(f"{rect.get_height():.1f}", (rect.get_x() + rect.get_width() / 2,
                    rect.get_height()), ha="center", va="bottom", fontsize=6.3, color=MUTED)
ax.set_xticks(list(x), metrics)
ax.set_ylabel("Share of repositories (%)")
ax.set_ylim(0, 75)
ax.spines[["top", "right"]].set_visible(False)
ax.yaxis.grid(True, linewidth=0.3, color=GRID)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper right")
fig.tight_layout()
fig.savefig("fig_governance.pdf")
print("fig_governance.pdf")

# ---------- Fig 3: rule shape ----------
def rule_shares(rows, key_ok=None):
    """rule -> share of scannable repos failing it."""
    per_repo = {}
    rule_repos = defaultdict(set)
    for r in rows:
        if key_ok and not key_ok(r):
            continue
        if r["failed"] in ("clone_error", "scan_error"):
            per_repo.setdefault(r["repo"], None)
            continue
        d = per_repo.get(r["repo"])
        if d is None:
            d = per_repo[r["repo"]] = {"passed": int(r["passed"] or 0),
                                       "failed": int(r["failed"] or 0)}
        if r["check_id"]:
            rule_repos[r["check_id"]].add(r["repo"])
    scannable = {k for k, v in per_repo.items() if v and v["passed"] + v["failed"] > 0}
    return ({c: 100 * len(rs & scannable) / len(scannable) for c, rs in rule_repos.items()},
            len(scannable))


excl_rows = load(DATA / "scan_absent.csv")
p4_rows = []
for p in ("aws", "azurerm", "google"):
    p4_rows.extend(load(P4 / f"scan_{p}.csv"))


def in_tofu(r):
    parts = (r["module_id"] or "").split("/")
    return pres.get(tuple(parts[:3])) == "True" if len(parts) >= 3 else False


excl_share, n_excl = rule_shares(excl_rows)
shared_share, n_shared = rule_shares(p4_rows, in_tofu)

SHORT = {
    "CKV_TF_1": "Module source not commit-pinned",
    "CKV_GCP_32": "Project-wide SSH keys allowed",
    "CKV_GCP_40": "Compute instance has public IP",
    "CKV_GCP_39": "Shielded VM disabled",
    "CKV_GCP_62": "Bucket access logging off",
    "CKV_GCP_114": "GCS public-access prevention off",
    "CKV2_AWS_62": "S3 event notifications off",
    "CKV_AWS_356": "IAM policy wildcard resource",
    "CKV_AWS_144": "S3 cross-region replication off",
    "CKV_AWS_145": "S3 not KMS-encrypted",
}
top = sorted(excl_share.items(), key=lambda kv: -kv[1])[:10]
labels = [f"{SHORT.get(c, c)} ({c})" for c, _ in top][::-1]
ev = [v for _, v in top][::-1]
sv = [shared_share.get(c, 0.0) for c, _ in top][::-1]

fig, ax = plt.subplots(figsize=(3.5, 2.6))
y = range(len(ev))
h = 0.38
ax.barh([i + h / 2 for i in y], ev, h, color=VERM, hatch="///", edgecolor="white",
        linewidth=0.3, label=f"tf-exclusive (n={n_excl})")
ax.barh([i - h / 2 for i in y], sv, h, color=BLUE, label=f"shared (n={n_shared})")
ax.set_yticks(list(y), labels, fontsize=6.3)
ax.set_xlabel("Scannable repositories failing the rule (%)")
ax.spines[["top", "right"]].set_visible(False)
ax.xaxis.grid(True, linewidth=0.3, color=GRID)
ax.set_axisbelow(True)
ax.set_xlim(0, max(max(ev), max(sv)) * 1.12)
ax.legend(frameon=False, loc="lower right")
fig.tight_layout()
fig.savefig("fig_rules.pdf")
print("fig_rules.pdf")

print(f"\n[check] tf-exclusive scannable={n_excl}  shared-baseline scannable={n_shared}")
print(f"[check] governance shared n={vals['shared_n']} tf-exclusive n={vals['tf-exclusive_n']}")
