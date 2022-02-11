## 0.52 (2022-02-11)

#### New rules

- dataproc/BP/2022_001: Cloud Monitoring agent is enabled.
- dataproc/ERR/2022_002: Dataproc is not using deprecated images.
- gce/WARN/2022_001: IAP service can connect to SSH/RDP port on instances.
- gce/WARN/2022_002: Instance groups named ports are using unique names.
- gke/ERR/2022_002: GKE nodes of private clusters can access Google APIs and services.
- gke/ERR/2022_003: GKE connectivity: load balancer to node communication (ingress).

#### Updated rules

- gcb/ERR/2022_001: Fix false positive when no build is configured.
- gke/WARN/2021_008: Improve Istio deprecation message

#### Enhancements

- Introduce "extended" rules (BP_EXT, ERR_EXT, etc.), disabled by default
  and which can be enabled with --include-extended.
- Large IAM policy code refactorings in preparation for org-level IAM
  policy support.

#### Fixes

- More API retry fixes.
- Fix --billing-project which had no effect before.

## 0.51 (2022-01-21)

#### Fixes

- Update Python dependencies, and add 'packaging', missing in the docker image.

## 0.50 (2022-01-21)

#### New rules

- gcb/ERR/2022_001: The Cloud Build logs do not report permission issues
- gce/BP/2021_002: GCE nodes have an up to date ops agent
- gce/BP/2021_003: Secure Boot is enabled
- gce/ERR/2021_004: Serial logs don’t contain Secure Boot errors
- gce/ERR/2021_005: Serial logs don't contain mount error messages
- gce/WARN/2021_005: Serial logs don't contain out-of-memory messages
- gce/WARN/2021_006: Serial logs don't contain "Kernel panic" messages
- gce/WARN/2021_007: Serial logs don't contain "BSOD" messages
- gcs/BP/2022_001: Buckets are using uniform access
- gke/BP/2022_001: GKE clusters are regional
- gke/ERR/2022_001: GKE connectivity: pod to pod communication
- gke/WARN/2022_001: GKE clusters with workload identity are regional
- gke/WARN/2022_002: GKE metadata concealment is not in use

#### Updated rules

- gcf/WARN/2021_001: add one more deprecated runtime Nodejs6 (github #17)

#### Enhancements

- New product: App Engine Standard
- New product: Cloud Build
- New product: Cloud Pub/Sub
- New product: Cloud Storage

#### Fixes

- Verify early that IAM API is enabled
- Catch API errors in prefetch_rule
- Disable italic in Cloud Shell
- Implement retry logic for batch API failures

## 0.49 (2021-12-20)

#### New / updated rules

- dataproc/BP/2021_001: Dataproc Job driver logs are enabled
- composer/WARN/2021_001: Composer environment status is running (b/207615409)
- gke/ERR/2021_013: GKE cluster firewall rules are configured. (b/210407018)
- gke/ERR/2021_014: GKE masters of can reach the nodes. (b/210407018)
- gke/ERR/2021_015: GKE connectivity: node to pod communication. (b/210407018)
- gce/WARN/2021_001: verify logging access scopes (b/210711351)
- gce/WARN/2021_003: verify monitoring access scopes (b/210711351)

#### Enhancements

- New product: Cloud Composer (b/207615409)
- Simplify API testing by using ephemeral projects (b/207484323)
- gcpdiag.sh wrapper script now verifies the minimum version of current script
- Add support for client-side firewall connectivity tests (b/210407018)

#### Fixes

## 0.48 (2021-11-15)

#### New rules

- apigee/WARN/2021_001: Every env. group has at least one env. (b/193733957)
- dataproc/WARN/2021_001: Dataproc cluster is in RUNNING state (b/204850980)

#### Enhancements

- Use OAuth authentication by default (b/195908593)
- New product: Dataproc (b/204850980)
- New product: Apigee (b/193733957)

#### Fixes

- Fix GitHub actions with newest pipenv

## 0.47 (2021-11-01)

#### New rules

- gce/WARN/2021_004: check serial output for 'disk full' messages (b/193383069)

#### Enhancements

- Add podman support in wrapper script

#### Fixes

- Fix gcf KeyError when API enabled but no functions defined (b/204516746)

## 0.46 (2021-10-27)

#### New rules

- gce/WARN/2021_003: gce service account monitoring permissions (b/199277342)
- gcf/WARN/2021_001: cloud functions deprecated runtimes
- gke/WARN/2021_009: deprecated node image types (b/202405661)

#### Enhancements

- New website! https://gcpdiag.dev
- Rule documentation permalinks added to lint output (b/191612825)
- Added --include and --exclude arguments to filter rules to run (b/183490284)


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
