"""Paper 4 step 3 (RQ2): scan module defaults with checkov.

Usage:
    python clone_and_scan.py --modules modules_azurerm.csv modules_aws.csv modules_google.csv \
                             --top 100 --workdir _repos --out scan_results.csv

Shallow-clones the default branch of the top-N modules per provider CSV and runs
checkov (terraform framework) against each. Insecure-default detection reuses
checkov's rule IDs (citable, reproducible) rather than hand-rolled regexes.
Resumable: repos already present in --out are skipped.

# ponytail: scans latest default branch only; per-major-version scans (RQ4
# provider-coupling) need clone-per-tag — add after core RQ2 numbers validate.
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

FIELDS = ["module_id", "repo", "provider", "downloads",
          "passed", "failed", "check_id", "check_name", "resource", "file"]


def repo_of(source):
    m = re.search(r"github\.com/([^/]+/[^/\s]+)", source or "")
    return m.group(1).removesuffix(".git") if m else None


def run_checkov(path: str) -> dict | None:
    out_dir = tempfile.mkdtemp()
    code = subprocess.run(
        [sys.executable, "-c",
         "import sys; from checkov.main import Checkov; "
         "c = Checkov(argv=sys.argv[1:]); c.run(); c.print_results()",
         "-d", path, "--framework", "terraform", "-o", "json",
         "--output-file-path", out_dir, "--quiet", "--compact",
         # module defaults only — example/test code is not what consumers deploy
         "--skip-path", "examples", "--skip-path", "example",
         "--skip-path", "tests", "--skip-path", "test"],
        capture_output=True, text=True, timeout=600,
    )
    result_file = os.path.join(out_dir, "results_json.json")
    if not os.path.exists(result_file):
        print(f"  checkov produced no output (rc={code.returncode})", file=sys.stderr)
        shutil.rmtree(out_dir, ignore_errors=True)
        return None
    with open(result_file, encoding="utf-8") as f:
        data = json.load(f)
    shutil.rmtree(out_dir, ignore_errors=True)
    # checkov emits a list when multiple frameworks matched
    if isinstance(data, list):
        data = next((d for d in data if d.get("check_type") == "terraform"), data[0] if data else None)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modules", nargs="+", required=True)
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--workdir", default="_repos")
    ap.add_argument("--out", default="scan_results.csv")
    args = ap.parse_args()

    os.makedirs(args.workdir, exist_ok=True)

    targets = {}  # repo -> row (dedupe, keep first/highest-download occurrence)
    for path in args.modules:
        with open(path, newline="", encoding="utf-8") as f:
            rows = sorted(csv.DictReader(f), key=lambda r: int(r.get("downloads") or 0), reverse=True)
        for row in rows[: args.top]:
            repo = repo_of(row.get("source"))
            if repo and repo not in targets:
                targets[repo] = row

    done = set()
    if os.path.exists(args.out):
        with open(args.out, newline="", encoding="utf-8") as f:
            done = {r["repo"] for r in csv.DictReader(f)}

    new_file = not os.path.exists(args.out)
    with open(args.out, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()

        todo = [r for r in targets if r not in done]
        print(f"{len(targets)} repos, {len(done)} done, {len(todo)} to scan", file=sys.stderr)

        for i, repo in enumerate(todo, 1):
            row = targets[repo]
            dest = os.path.join(args.workdir, repo.replace("/", "__"))
            if not os.path.exists(dest):
                rc = subprocess.run(
                    ["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", dest],
                    capture_output=True, text=True, timeout=300,
                ).returncode
                if rc != 0:
                    print(f"  clone failed: {repo}", file=sys.stderr)
                    w.writerow({"module_id": row["id"], "repo": repo,
                                "provider": row["provider"], "downloads": row["downloads"],
                                "passed": "", "failed": "clone_error"})
                    f.flush()
                    continue
            try:
                data = run_checkov(dest)
            except subprocess.TimeoutExpired:
                data = None
            if not data:
                w.writerow({"module_id": row["id"], "repo": repo,
                            "provider": row["provider"], "downloads": row["downloads"],
                            "passed": "", "failed": "scan_error"})
            else:
                summary = data.get("summary", {})
                failed_checks = (data.get("results") or {}).get("failed_checks", [])
                base = {"module_id": row["id"], "repo": repo,
                        "provider": row["provider"], "downloads": row["downloads"],
                        "passed": summary.get("passed"), "failed": summary.get("failed")}
                if not failed_checks:
                    w.writerow(base)
                for c in failed_checks:
                    w.writerow({**base,
                                "check_id": c.get("check_id"),
                                "check_name": c.get("check_name"),
                                "resource": c.get("resource"),
                                "file": c.get("file_path")})
            f.flush()
            shutil.rmtree(dest, ignore_errors=True)  # keep disk bounded
            if i % 10 == 0:
                print(f"  {i}/{len(todo)} scanned", file=sys.stderr)

    print(f"Done -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
