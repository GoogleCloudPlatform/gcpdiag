## 0.45 (2021-10-08)

#### Enhancements

- Use --auth-adc by default for all non-google.com users (b/202488675)

## 0.44 (2021-10-07)

#### New rules

- gke/ERR/2021_009: gke cluster and node pool version skew (b/200559114)
- gke/ERR/2021_010: clusters are not facing ILB quota issues (b/193382041)
- gke/ERR/2021_011: ip-masq-agent errors (b/199480284)
- iam/SEC/2021_001: no service account has owner role (b/201526416)

#### Enhancements

- Improve error message for --auth-adc authentication errors (b/202091830)
- Suggest gcloud command if CRM API is not enabled
- Use --auth-adc by default in Cloud Shell (b/201996404)
- Improve output with hidden items
- Update docker image to python:3.9-slim

#### Fixes

- Make the docker wrapper macos-compatible (GH-10)
- Exclude fleet workload identities from SA disabled check (b/201631248)
