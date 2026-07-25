# Paper 10 — "One Ecosystem, Two Registries: Terraform vs OpenTofu After the Fork"

**Genre:** mining study (Paper 4's pipeline, cross-registry — executes
Paper 4's own stated future work). **Venue path:** MSR (mining venue) →
UCC → IEEE Access.
**Gap:** the OpenTofu fork is the biggest governance event in IaC; nobody
has measured what it did to the module supply chain. All public data, $0.

## RQs
- RQ1: Population divergence — overlap of top modules between
  registry.terraform.io and the OpenTofu registry; which modules exist in
  one only; download/adoption asymmetry where exposed.
- RQ2: Governance delta — maintenance health (Paper 4 metrics: archived,
  dormancy, bus factor) of the shared vs registry-exclusive populations;
  does the fork's community skew differ?
- RQ3: Drift since fork — for shared modules, version currency across the
  two registries (does one serve stale versions?); provider constraint
  divergence (tofu-specific features adoption).
- RQ4: Security defaults — checkov (pinned version) on the OpenTofu-side
  top-100 vs Paper 4's Terraform-side results: same 87.4%/58% shape or not?

## Method
Adapt collect.py to the OpenTofu registry API; reuse github_meta.py,
clone_and_scan.py, analyze.py unchanged (they're registry-agnostic past
collection — exactly what Paper 4's repo README promises). New snapshot of
BOTH registries same day for comparability. Cross-cite Papers 4↔10.

## Cost
$0 (API + clones). First in the execution queue.

## Status
- [x] collect_tofu.py + dual-registry snapshot (snapshot.py, 2026-07-18)
- [x] Pipeline runs both sides
- [x] All four RQs analyzed (analyze.py, rq24_analyze.py, extras.py) → results.md
- [x] Figures: fig_presence.pdf, fig_governance.pdf, fig_rules.pdf (make_figures.py);
      fig_pipeline10.png architecture diagram (make_arch_diagram.py)
- [x] 10pp draft compiled 2026-07-23 (paper.tex + refs.bib → title-named PDF)
- [ ] **USER VALIDATES every number in results.md against data/*.csv**
- [ ] **USER opens and reads every refs.bib entry** (none web-verified)
- [ ] Companion repo published → fill Artifact Availability URL
- [ ] Zenodo upload (user) → venue: MSR → UCC → IEEE Access
