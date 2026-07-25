# Paper 10 results — dual-registry snapshot 2026-07-18

## RQ1 — presence of Terraform top-500 modules in OpenTofu

- aws: present 392 (78.4%), absent 108 (21.6%)
- azurerm: present 275 (55.0%), absent 225 (45.0%)
- google: present 360 (72.0%), absent 140 (28.0%)
- community: present 935 (74.6%), absent 318 (25.4%)
- official: present 92 (37.2%), absent 155 (62.8%)
- download-weighted presence: 95.2% of TF-side downloads map to modules that exist in OpenTofu; 4.8% do not

## RQ3 — version currency of shared modules

- comparable shared pairs: 1027
- identical latest version: 1004 (97.8%)
- Terraform side newer (OpenTofu stale): 7 (0.7%)
- OpenTofu side newer: 14 (1.4%)
- stale examples: riboseinc/codecommit-sqs/aws: tf 1.2.0 vs tofu 1.1.1; buildo/cranehost/aws: tf 2.0.0 vs tofu 1.4.2; devops-workflow/lb/aws: tf 3.50.0 vs tofu 3.5.0; trussworks/ecs-cluster/aws: tf 3.1.0 vs tofu 3.0.2; aztfmod/caf-azure-firewall/azurerm: tf 2.1.0 vs tofu 0.1.2

## OpenTofu index shape (full 22k index)

- modules indexed: 22290
- released within last 12 months: 2852 (12.8%)
- top targets: [('aws', 10177), ('azurerm', 2206), ('google', 1161), ('azure', 786), ('kubernetes', 467), ('module', 421), ('shoreline', 395), ('beginner', 361)]
- registry exposes NO download counts (design difference; popularity proxy = GitHub stars via detail endpoint)
