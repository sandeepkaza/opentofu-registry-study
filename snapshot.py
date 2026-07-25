"""Paper 10 dual-registry snapshot: Terraform Registry vs OpenTofu Registry.

Produces, in ./data (snapshot date recorded in every row):
  modules_tf_{aws,azurerm,google}.csv   fresh Terraform-side top-500 (Paper 4 method)
  tofu_index.csv                        full OpenTofu module index (one row per module)
  tofu_details_matched.csv              OpenTofu detail records (popularity/forks/blocked)
                                        for every module in the Terraform top-500 sets
Run:  python snapshot.py            (long-running; polite 1 rps to each API)
"""

import csv
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests

SNAP = date.today().isoformat()
DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

TF_REGISTRY = "https://registry.terraform.io/v1/modules"
TOFU_INDEX = "https://api.opentofu.org/registry/docs/modules/index.json"
TOFU_DETAIL = "https://api.opentofu.org/registry/docs/modules/{ns}/{name}/{target}/index.json"
PROVIDERS = ["aws", "azurerm", "google"]
TOP = 500


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def collect_terraform(provider):
    out = DATA / f"modules_tf_{provider}.csv"
    modules, offset = [], 0
    while len(modules) < TOP * 2:  # overfetch, sort client-side (Paper 4 method)
        r = requests.get(TF_REGISTRY, params={"provider": provider,
                                              "limit": 100, "offset": offset}, timeout=30)
        r.raise_for_status()
        batch = r.json().get("modules", [])
        if not batch:
            break
        modules.extend(batch)
        offset += 100
        time.sleep(1.0)
    modules.sort(key=lambda m: m.get("downloads", 0), reverse=True)
    modules = modules[:TOP]
    fields = ["snapshot_date", "id", "namespace", "name", "provider", "downloads",
              "verified", "source", "published_at", "latest_version", "description"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for m in modules:
            w.writerow({
                "snapshot_date": SNAP, "id": m.get("id"),
                "namespace": m.get("namespace"), "name": m.get("name"),
                "provider": m.get("provider"), "downloads": m.get("downloads"),
                "verified": m.get("verified"), "source": m.get("source"),
                "published_at": m.get("published_at"),
                "latest_version": m.get("version"),
                "description": (m.get("description") or "").replace("\n", " "),
            })
    log(f"terraform {provider}: {len(modules)} rows -> {out.name}")
    return modules


def collect_tofu_index():
    log("downloading OpenTofu index...")
    r = requests.get(TOFU_INDEX, timeout=120)
    r.raise_for_status()
    mods = r.json()["modules"]
    out = DATA / "tofu_index.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["snapshot_date", "namespace", "name", "target",
                    "n_versions", "latest_version", "latest_published",
                    "first_published", "description"])
        for m in mods:
            a = m["addr"]
            vs = m.get("versions", [])
            w.writerow([SNAP, a["namespace"], a["name"], a["target"], len(vs),
                        vs[0]["id"] if vs else "", vs[0]["published"] if vs else "",
                        vs[-1]["published"] if vs else "",
                        (m.get("description") or "").replace("\n", " ")[:200]])
    log(f"tofu index: {len(mods)} rows -> {out.name}")
    return mods


def collect_tofu_details(tf_sets):
    """Fetch OpenTofu detail for every Terraform-side top-500 module."""
    out = DATA / "tofu_details_matched.csv"
    seen = set()
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["snapshot_date", "namespace", "name", "target", "exists_in_tofu",
                    "popularity", "fork_count", "is_blocked", "n_versions",
                    "latest_version", "latest_published"])
        for provider, mods in tf_sets.items():
            for m in mods:
                key = (m["namespace"], m["name"], provider)
                if key in seen:
                    continue
                seen.add(key)
                url = TOFU_DETAIL.format(ns=m["namespace"], name=m["name"], target=provider)
                try:
                    r = requests.get(url, timeout=30)
                    if r.status_code == 404:
                        w.writerow([SNAP, m["namespace"], m["name"], provider,
                                    False, "", "", "", "", "", ""])
                    else:
                        r.raise_for_status()
                        d = r.json()
                        vs = d.get("versions", [])
                        w.writerow([SNAP, m["namespace"], m["name"], provider, True,
                                    d.get("popularity"), d.get("fork_count"),
                                    d.get("is_blocked"), len(vs),
                                    vs[0]["id"] if vs else "",
                                    vs[0]["published"] if vs else ""])
                except Exception as e:  # log and continue; row marked error
                    w.writerow([SNAP, m["namespace"], m["name"], provider,
                                "ERROR", str(e)[:80], "", "", "", "", ""])
                if len(seen) % 100 == 0:
                    log(f"  tofu details: {len(seen)} fetched")
                    f.flush()
                time.sleep(0.7)
    log(f"tofu details: {len(seen)} rows -> {out.name}")


def main():
    log(f"SNAPSHOT {SNAP}")
    tf_sets = {p: collect_terraform(p) for p in PROVIDERS}
    collect_tofu_index()
    collect_tofu_details(tf_sets)
    log("SNAPSHOT COMPLETE")


if __name__ == "__main__":
    main()
