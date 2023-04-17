## 0.59 (2023-04-14)

#### New rules

- apigee/ERR/2023\_001: Customer's network is peered to Apigee's network
- apigee/ERR/2023\_002: Network bridge managed instance group is correctly configured
- bigquery/WARN/2022\_003: BigQuery copy job does not exceed the daily copy quota
- bigquery/WARN/2022\_004: BigQuery copy job does not exceed the cross-region daily copy quota
- bigquery/WARN/2023\_001: BigQuery query job does not time out during execution
- composer/WARN/2022\_003: Composer scheduler parses all DAG files without overloading
- datafusion/ERR/2022\_008: Cloud Data Fusion SA has Service Account User permissions on the Dataproc SA
- datafusion/ERR/2022\_009: Cloud Dataproc Service Account has a Cloud Data Fusion Runner role
- datafusion/ERR/2022\_010: Cloud Dataproc Service Account has a Dataproc Worker role
- datafusion/ERR/2022\_011: The Dataproc SA for a CDF instance with version > 6.2.0 has Storage Admin role
- dataproc/ERR/2022\_004: Dataproc on GCE master VM is able to communicate with atleast one worker VM
- dataproc/ERR/2023\_001: Dataproc cluster initialization completed by the end of the timeout period
- dataproc/WARN/2022\_004: Cluster should normally spend most of the time in RUNNING state
- dataproc/WARN/2023\_001: Concurrent Job limit was not exceeded
- dataproc/WARN/2023\_002: Master Node System Memory utilization under threshold
- gae/ERR/2023\_001: App Engine: VPC Connector creation failure due to Org Policy
- gae/ERR/2023\_002: App Engine: VPC Connector creation due to subnet overlap
- gcb/ERR/2022\_004: Cloud Build Service Agent has the cloudbuild.serviceAgent role
- gce/BP/2023\_001: GCE Instances follows access scope best practice
- gce/BP/2023\_001: Instance time source is configured with Google NTP server
- gce/ERR/2022\_002: Serial logs don't contain Guest OS activation errors
- gce/WARN/2022\_010: GCE has enough resources available to fulfill requests
- gce/WARN/2022\_011: GCE VM service account is valid
- gce/WARN/2022\_012: Validate if a Microsoft Windows instance is able to activate using GCP PAYG licence
- gke/BP/2023\_001: GKE network policy minimum requirements
- gke/BP/2023\_002: Stateful workloads do not run on preemptible node
- gke/BP/2023\_004: GKE clusters are VPC-native
- gke/BP_EXT/2023\_003: GKE maintenance windows are defined
- gke/ERR/2023\_001: Container File System API quota not exceeded
- gke/ERR/2023\_002: GKE private clusters are VPC-native
- gke/ERR/2023\_003: containerd config.toml is valid
- gke/WARN/2023\_001: Container File System has the required scopes for Image Streaming
- gke/WARN/2023\_002: GKE workload timeout to Compute Engine metadata server
- lb/BP/2022\_001: LocalityLbPolicy compatible with sessionAffinity
- notebooks/ERR/2023\_001: Vertex AI Workbench user-managed notebook instances are healthy
- vpc/BP/2022\_001: Explicit routes for Google APIs if the default route is modified
- vpc/BP/2023\_001: DNS logging is enabled for public zones

#### Enhancements

- New product: Cloud Load Balancing
- New product: Vertex AI Workbench Notebooks
- Experimental asynchronous IO execution (not enabled by default)
- gcb/ERR/2022\_002: Check access to images hosted in gcr.io repositories
- Add support for interconnect API
- Extract project id from email when fetching service accounts instead of using
  wildcard, making IAM service account checks more reliable.
- --project now accepts project numbers in addition to project ids

#### Fixes

- gke/BP/2022\_003: updated EOL schedule for GKE
- Fix 403 error on userinfo API call

## 0.58 (2022-11-08)

#### Deprecation

- Python 3.9+ is required for gcpdiag. Python 3.8 and older versions support is deprecated.
- Deprecated authentication using OAuth (`--auth-oauth`) has been removed.

#### New rules

- apigee/ERR/2022\_002: Verify whether Cloud KMS key is enabled and could be accessed by Apigee Service Agent
- datafusion/ERR/2022\_003: Private Data Fusion instance is peered to the tenant project
- datafusion/ERR/2022\_004: Cloud Data Fusion Service Account has necessary permissions
- datafusion/ERR/2022\_005: Private Data Fusion instance has networking permissions
- datafusion/ERR/2022\_006: Private Google Access enabled for private Data Fusion instance subnetwork
- datafusion/ERR/2022\_007: Cloud Data Fusion Service Account exists at a Project
- gke/BP/2022\_004: GKE clusters should have HTTP load balancing enabled to use GKE ingress

#### Enhancements

- Python dependencies updated

#### Fixes

- gke/ERR/2021\_002: skip if there are no GKE clusters



## 0.57 (2022-09-29)

#### Deprecation

- Default authentication using OAuth (`--auth-oauth`) is now deprecated and Application Default Credentials (`--auth-adc`) will be used instead. Alternatively you can use Service Account private key (`--auth-key FILE`).

#### New rules

- apigee/WARN/2022\_001: Verify whether all environments has been attached to Apigee X instances
- apigee/WARN/2022\_002: Environment groups are created in the Apigee runtime plane
- cloudrun/ERR/2022\_001: Cloud Run service agent has the run.serviceAgent role
- datafusion/ERR/2022\_001: Firewall rules allow for Data Fusion to communicate to Dataproc VMs
- datafusion/ERR/2022\_002: Private Data Fusion instance has valid host VPC IP range
- dataproc/WARN/2022\_001: Dataproc VM Service Account has necessary permissions
- dataproc/WARN/2022\_002: Job rate limit was not exceeded
- gcf/ERR/2022\_002: Cloud Function deployment failure due to Resource Location Constraint
- gcf/ERR/2022\_003: Function invocation interrupted due to memory limit exceeded
- gke/WARN/2022/\_008: GKE connectivity: possible dns timeout in some gke versions
- gke/WARN/2022\_007: GKE nodes need Storage API access scope to retrieve build artifacts
- gke/WARN/2022\_008: GKE connectivity: possible dns timeout in some gke versions

#### Enhancements

- New product: Cloud Run
- New product: Data Fusion

#### Fixes

- gcf/WARN/2021\_002: Added check for MATCH_STR
- gcs/BP/2022\_001: KeyError: 'iamConfiguration'
- gke/ERR/2022\_003: unhandled exception
- gke/WARN/2022\_005: Incorrectly report missing "nvidia-driver-installer" daemonset
- iam/SEC/2021\_001: unhandled exception



## 0.56 (2022-07-18)

#### New rules

- bigquery/ERR/2022\_001: BigQuery is not exceeding rate limits
- bigquery/ERR/2022\_001: BigQuery jobs not failing due to concurrent DML updates on the same table
- bigquery/ERR/2022\_002: BigQuery jobs are not failing due to results being larger than the maximum response size
- bigquery/ERR/2022\_003: BigQuery jobs are not failing while accessing data in Drive due to a permission issue
- bigquery/ERR/2022\_004: BigQuery jobs are not failing due to shuffle operation resources exceeded
- bigquery/WARN/2022\_002: BigQuery does not violate column level security
- cloudsql/WARN/2022\_001: Docker bridge network should be avoided
- composer/WARN/2022\_002: fluentd pods in Composer enviroments are not crashing
- dataproc/ERR/2022\_003: Dataproc Service Account permissions
- dataproc/WARN/2022\_001: Dataproc clusters are not failed to stop due to the local SSDs
- gae/WARN/2022\_002: App Engine Flexible versions don't use deprecated runtimes
- gcb/ERR/2022\_002: Cloud Build service account registry permissions
- gcb/ERR/2022\_003: Builds don't fail because of retention policy set on logs bucket
- gce/BP/2022\_003: detect orphaned disks
- gce/ERR/2022\_001: Project limits were not exceeded
- gce/WARN/2022\_004: Cloud SQL Docker bridge network should be avoided
- gce/WARN/2022\_005: GCE CPU quota is not near the limit
- gce/WARN/2022\_006: GCE GPU quota is not near the limit
- gce/WARN/2022\_007: VM has the proper scope to connect using the Cloud SQL Admin API
- gce/WARN/2022\_008: GCE External IP addresses quota is not near the limit
- gce/WARN/2022\_009: GCE disk quota is not near the limit
- gcf/ERR/2022\_001: Cloud Functions service agent has the cloudfunctions.serviceAgent role
- gcf/WARN/2021\_002: Cloud Functions have no scale up issues
- gke/BP\_EXT/2022\_001: Google Groups for RBAC enabled (github #12)
- gke/WARN/2022\_006: GKE NAP nodes use a containerd image
- tpu/WARN/2022\_001: Cloud TPU resource availability
- vpc/WARN/2022\_001: Cross Project Networking Service projects quota is not near the limit

#### Updated rules

- dataproc/ERR/2022\_002: fix os version detection (github #26)
- gke/BP/2022\_003: update GKE EOL schedule
- gke/ERR/2022\_001: fix KeyError exception
- gke/BP/2022\_002: skip legacy VPC

#### Enhancements

- Add support for multiple output formats (--output=csv, --output=json)
- Better handle CTRL-C signal
- Org policy support
- New product: CloudSQL
- New product: VPC
- Renamed product "GAES" to "GAE" (Google App Engine)
- Publish internal API documentation on https://gcpdiag.dev/docs/development/api/
- Update Python dependencies

## 0.55 (2022-04-25)

Version 0.55 was released with the same code as 0.54. The release was used
to facilitate the transition of binaries to another location.

## 0.54 (2022-04-25)

#### New rules

- apigee/ERR/2022_001: Apigee Service Agent permissions

#### Enhancements

- dynamically load gcpdiag lint rules for all products
- support IAM policy retrieval for Artifact Registry
- move gcpdiag release buckets to new location

#### Fixes

- gke/ERR/2022_002: use correct network for shared VPC scenario (#24)
- error out early if service accounts of inspected projects can't be retrieved
- fix docker wrapper script for --config and --auth-key options
- allow to create test projects in an org folder
- ignore more system service accounts (ignore all accounts starting with gcp-sa)

## 0.53 (2022-03-30)

#### New rules

- composer/ERR/2022_001: Composer Service Agent permissions
- composer/ERR/2022_002: Composer Environment Service Account permissions
- composer/WARN/2022_001: Composer Service Agent permissions for Composer 2.x
- gce/BP_EXT/2022_001: GCP project has VM Manager enabled
- gce/WARN/2022_003: GCE VM instances quota is not near the limit
- gke/BP/2022_002: GKE clusters are using unique subnets
- gke/BP/2022_003: GKE cluster is not near to end of life
- gke/WARN/2022_003: GKE service account permissions to manage project firewall rules
- gke/WARN/2022_004: Cloud Logging API enabled when GKE logging is enabled
- gke/WARN/2022_005: NVIDIA GPU device drivers are installed on GKE nodes with GPU

#### Enhancements

- Support IAM policies for service accounts and subnetworks
- Skip rules using logs if Cloud Logging API is disabled
- New option: --logs-query-timeout
- Add support for configuration files
  (see https://gcpdiag.dev/docs/usage/#configuration-file)

#### Fixes

- Fix various unhandled exceptions

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
- Fix exception related to GCE instance scopes.

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
