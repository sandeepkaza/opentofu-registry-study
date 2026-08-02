"""Paper 10 analysis: Terraform vs OpenTofu registry divergence.

Reads data/*.csv from snapshot.py; writes results.md aggregates.
All numbers derive from the committed snapshot CSVs.
"""

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).parent / "data"
OUT = Path(__file__).parent / "results.md"

OFFICIAL = {"Azure", "aws-ia", "terraform-aws-modules", "GoogleCloudPlatform",
            "terraform-google-modules", "hashicorp", "oracle-terraform-modules"}


def load_tf():
    tf = {}
    for p in ("aws", "azurerm", "google"):
        for r in csv.DictReader(open(DATA / f"modules_tf_{p}.csv", encoding="utf-8")):
            tf[(r["namespace"], r["name"], p)] = r
    return tf


def load_details():
    det = {}
    for r in csv.DictReader(open(DATA / "tofu_details_matched.csv", encoding="utf-8")):
        det[(r["namespace"], r["name"], r["target"])] = r
    return det


def norm_ver(v):
    return (v or "").lstrip("v")


def main():
    tf = load_tf()
    det = load_details()
    snap = next(iter(tf.values()))["snapshot_date"]

    lines = [f"# Paper 10 results — dual-registry snapshot {snap}\n"]

    # RQ1 overlap
    lines.append("## RQ1 — presence of Terraform top-500 modules in OpenTofu\n")
    per = defaultdict(lambda: [0, 0])  # provider -> [present, absent]
    strat = defaultdict(lambda: [0, 0])  # official/community -> [present, absent]
    dl_present = dl_absent = 0
    for key, r in tf.items():
        d = det.get(key)
        if not d or d["exists_in_tofu"] == "ERROR":
            continue
        present = d["exists_in_tofu"] == "True"
        per[key[2]][0 if present else 1] += 1
        s = "official" if r["namespace"] in OFFICIAL else "community"
        strat[s][0 if present else 1] += 1
        dl = int(r["downloads"] or 0)
        if present:
            dl_present += dl
        else:
            dl_absent += dl
    for p, (pr, ab) in sorted(per.items()):
        lines.append(f"- {p}: present {pr} ({pr/(pr+ab):.1%}), absent {ab} ({ab/(pr+ab):.1%})")
    for s, (pr, ab) in sorted(strat.items()):
        lines.append(f"- {s}: present {pr} ({pr/(pr+ab):.1%}), absent {ab} ({ab/(pr+ab):.1%})")
    tot_dl = dl_present + dl_absent
    lines.append(f"- download-weighted presence: {dl_present/tot_dl:.1%} of TF-side downloads "
                 f"map to modules that exist in OpenTofu; {dl_absent/tot_dl:.1%} do not\n")

    # RQ3 version currency for shared modules
    lines.append("## RQ3 — version currency of shared modules\n")
    same = tf_ahead = tofu_ahead = comp = 0
    examples_stale = []
    for key, r in tf.items():
        d = det.get(key)
        if not d or d["exists_in_tofu"] != "True":
            continue
        tv, ov = norm_ver(r["latest_version"]), norm_ver(d["latest_version"])
        if not tv or not ov:
            continue
        comp += 1
        if tv == ov:
            same += 1
        else:
            # compare tuples where parseable
            try:
                tvt = tuple(int(x) for x in tv.split(".")[:3])
                ovt = tuple(int(x) for x in ov.split(".")[:3])
                if tvt > ovt:
                    tf_ahead += 1
                    if len(examples_stale) < 10:
                        examples_stale.append(f"{key[0]}/{key[1]}/{key[2]}: tf {tv} vs tofu {ov}")
                elif ovt > tvt:
                    tofu_ahead += 1
                else:
                    same += 1
            except ValueError:
                pass
    lines.append(f"- comparable shared pairs: {comp}")
    lines.append(f"- identical latest version: {same} ({same/comp:.1%})")
    lines.append(f"- Terraform side newer (OpenTofu stale): {tf_ahead} ({tf_ahead/comp:.1%})")
    lines.append(f"- OpenTofu side newer: {tofu_ahead} ({tofu_ahead/comp:.1%})")
    lines.append("- stale examples: " + "; ".join(examples_stale[:5]) + "\n")

    # tofu ecosystem shape (full index)
    lines.append("## OpenTofu index shape (full 22k index)\n")
    idx = list(csv.DictReader(open(DATA / "tofu_index.csv", encoding="utf-8")))
    now = datetime.fromisoformat(snap).replace(tzinfo=timezone.utc)
    n = len(idx)
    tgt = defaultdict(int)
    fresh12 = 0
    for r in idx:
        tgt[r["target"]] += 1
        lp = r["latest_published"]
        if lp:
            try:
                dtp = datetime.fromisoformat(lp.replace("Z", "+00:00"))
                if (now - dtp).days <= 365:
                    fresh12 += 1
            except ValueError:
                pass
    top_tgt = sorted(tgt.items(), key=lambda x: -x[1])[:8]
    lines.append(f"- modules indexed: {n}")
    lines.append(f"- released within last 12 months: {fresh12} ({fresh12/n:.1%})")
    lines.append(f"- top targets: {top_tgt}")
    lines.append("- registry exposes NO download counts (design difference; "
                 "popularity proxy = GitHub stars via detail endpoint)\n")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
