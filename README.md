# opentofu-registry-study

Companion artifact for the paper **"One Ecosystem, Two Registries: Measuring the Terraform-OpenTofu Fork's Effect on the Module Supply Chain"**.

A same-day dual-registry measurement of the Terraform-OpenTofu fork's effect on the module supply chain: presence, governance, drift, and security defaults.

## What's here

`data/` — the dual-registry snapshot: Terraform top-500 listings with per-module OpenTofu presence, the full OpenTofu index, matched detail records, repo metadata, and rule-level scan results.

## Reproduce

Requires Python 3 (plus, per paper, Docker/kind/a GPU host — see the paper's
Method section). Every number in the paper is regenerated from the committed
data by:

```bash
python3 analyze.py && python3 extras.py && python3 rq24_analyze.py
```

Each stage writes its intermediate data, so the path from raw measurement to
every reported figure is inspectable without re-running the measurement.

## Citation

See `CITATION.cff`. A DOI will be added after Zenodo archival. Venue path:
MSR -> UCC -> IEEE Access.

## License

MIT (`LICENSE`). Author: Venkata Sandeep Chowdary Kaza <sandeep.kaza@gmail.com>, ORCID 0009-0001-9454-8995.

## AI-assistance disclosure

AI-assisted scripting and editing (Anthropic Claude) was employed under the
author's direction; the author defined the research questions, designed the
method, ran the measurements, and validated every reported number.
