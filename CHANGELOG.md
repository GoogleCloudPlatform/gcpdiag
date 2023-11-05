## 0.66 (2023-10-13)

#### Fixes
- Handle app failure when project policy contains cross-project service accounts
- Update the version skew for modern versions of Kubernetes. https://kubernetes.io/blog/2023/08/15/kubernetes-v1-28-release/#changes-to-supported-skew-between-control-plane-and-node-versions
- Updating working and typos in multiple files
- Update gke test snapshot.
- added content in md file for rule apigee\_err\_2023\_003

#### New rules

- bigquery/ERR/2023\_008: user not authorized to perform this action
- pubsub/WARN/2023\_005: bigquery subscription has apt permissions
- asm/ERR/2023\_001, asm/ERR/2023\_002: Anthos Service mesh
- gke/BP/2022\_003: Make GKE EOL detection more robust and less hardcoded
- gke/WARN/2023\_004: Add a check for too low `maxPodsPerNode` number
- gke/ERR/2023\_012: missing memory request for hpa
- bigquery/ERR/2023\_006: bigquery policy does not belong to user
- pubsub/WARN/2023\_00[14]: no subscription without attached topic
- composer/WARN/2023\_009: Cloud Composer Intermittent Task Failure during Scheduling

#### New module
- Anthos Service mash


## 0.65 (2023-09-18)

#### New rules

- apigee/ERR/2023\_006: Multiple migs for multiple regions
- vertex/WARN/2023\_001: New product: Vertex AI / new rule: check featurestores state
- pubsub/WARN/2023\_001: Check that the project does not have a detached subscription
- gke/ERR/2023\_011: GKE Metadata Server isn’t reporting errors for pod IP not found
- dataflow/WARN/2023\_006: Dataflow job stuck in canceling state for more than half hour
- vpc/WARN/2023\_001: Private service access not exporting custom routes
- interconnect/WARN/2023\_001: Interconnect attachment is not using dataplane v1
- interconnect/WARN/2023\_002: Checking if the VLAN attachment is in a non functional state
- pubsub/WARN/2023\_003: Topic has at least one attached subscription
- bigquery/ERR/2023\_007: Data Transfer Service Agent exists and has the required roles
- bigquery/WARN/2023\_002: BigQuery subscriptions have deadletter topic attached
- dataproc/ERR/2023\_007: Enough resources in region for dataproc cluster creation
- interconnect/WARN/2023\_003: Interconnect link is under maintenance

#### Fixes

- Account for GKE zones in vpc/WARN/2023\_002
- Refactor GCE label reference
- Update pipenv
- Fix typing Union in notebooks
- Add prefetch\_rule to notebooks rules
- Use more descriptive name for get-subscriptions method and account for deleted topics


## 0.64 (2023-08-14)

#### New rules

- gke/bp\_2023\_005\_gateway\_crd: manually installed gateway crd GKE
- gke/err\_2023\_010\_nodelocal\_timeout: nodelocal dns timeout GKE
- gke/err\_2023\_009\_missing\_cpu\_req: Missing CPU request GKE
- gke/err\_2023\_008\_crashloopbackoff: gke cluster had pods in crashloopbackoff error GKE
- gke/err\_2023\_006\_gw\_controller\_annotation\_error: GKE Gateway controller reporting misconfigured annotations in Gateway resource GKE
- gke/err\_2023\_007\_gw\_controller\_http\_route\_misconfig: GKE Gateway controller reporting invalid HTTPRoute for Gateway GKE
- dataflow/bp\_2023\_001\_dataflow\_supported\_sdk\_version\_check: Dataflow job using supported sdk version dataflow
- cloudsql/warn\_2023\_003\_high\_mem\_usage: Cloud SQL instance's memory usage does not exceed 90%
- cloudsql/bp\_ext\_2023\_003\_auto\_storage\_increases: Cloud SQL instance autoscaling is enabled
- gke/warn\_2023\_003\_monitoring\_api\_disabled: Cloud Monitoring API enabled when GKE monitoring is enabled

#### Fixes

- Remove references to deprecated oauth option in docs b/281956212
- Update diagram titles to remove “gcp doctor” reference
- Fix wrong cloudsql/WARN/2023\_003 MQL query cloudsql (external submission)
- gcs/bp\_2022\_001\_bucket\_access\_uniform: skip cloud build and dataproc buckets issue/61 b/293951741
- gce/warn\_2022\_001\_iap\_tcp\_forwarding: skip check for dataproc cluster vm instances
- gce/bp\_2021\_001\_serial\_logging\_enabled: skip check for dataproc cluster vm instances
- gke/bp\_2022\_003\_cluster\_eol: end of life version list dates updated


## 0.63 (2023-07-10)

#### Fixes

-  Fix futures timeout error.

## 0.62 (2023-07-10)

#### New rules

- cloudsql/SEC/2023\_001: Cloud SQL is not publicly accessible (github #73)
- dataproc/ERR/2023\_002: Orphaned YARN application
- dataflow/ERR/2023\_007: Streaming Dataflow doesn't report being stuck because of firewall rules

#### Fixes

- Fix GCE API being erroneously required to run gcpdiag
- Fix locking issues in multi-threaded code
- Improve caching of API exceptions

## 0.61 (2023-06-30)

#### Fixes

- Fix attribute error on dnssec API call

## 0.60 (2023-06-29)

#### New rules

- apigee/ERR/2023\_003: Private Google Access (PGA) for subnet of Managed Instance Group is enabled
- apigee/ERR/2023\_004: Service Networking API is enabled and SA account has the required role
- apigee/ERR/2023\_005: External Load Balancer (XLB) is able to connect to the MIG
- bigquery/ERR/2023\_001: Jobs called via the API are all found
- bigquery/ERR/2023\_002: BigQuery hasn't reported any unknown datasets
- bigquery/ERR/2023\_003: BigQuery query job do not encounter resource exceeded error
- bigquery/ERR/2023\_004: BigQuery query job do not encounter dml concurrency issue
- bigquery/ERR/2023\_005: Scheduled query not failing due to outdated credentials
- bigquery/WARN/2023\_003: BigQuery query job does not fail with too many output columns error
- bigquery/WARN/2023\_004: BigQuery CMEK-related operations do not fail due to missing permissions
- bigquery/WARN/2023\_005: No errors querying wildcard tables
- cloudsql/BP/2023\_001: Cloud SQL is not assigned Public IP (github #65)
- cloudsql/BP/2023\_002: Cloud SQL is configured with automated backup
- cloudsql/BP\_EXT/2023\_001: Cloud SQL is defined with Maintenance Window as any (github #67)
- cloudsql/BP\_EXT/2023\_002: Cloud SQL is configured with Deletion Protection (github #68)
- cloudsql/BP\_EXT/2023\_003: Cloud SQL enables automatic storage increases feature
- cloudsql/BP\_EXT/2023\_004: Cloud SQL instance is covered by the SLA
- cloudsql/ERR/2023\_001: Cloud SQL instance should not be in SUSPENDED state
- cloudsql/WARN/2023\_001: Cloud SQL instance's log_output flag is not configured as TABLE
- cloudsql/WARN/2023\_002: Cloud SQL instance's avg CPU utilization is not over 98% for 6 hours
- cloudsql/WARN/2023\_003: Cloud SQL instance's memory usage does not exceed 90%
- composer/BP/2023\_001: Cloud Composer logging level is set to INFO
- composer/BP/2023\_002: Cloud Composer's worker concurrency is not limited by parallelism
- composer/BP/2023\_003: Cloud Composer does not override the StatsD configurations
- composer/BP\_EXT/2023\_001: Cloud Composer has no more than 2 Airflow schedulers
- composer/BP\_EXT/2023\_002: Cloud Composer has higher version than airflow-2.2.3
- composer/ERR/2023\_001: Cloud Composer is not in ERROR state
- composer/WARN/2023\_001: Cloud Composer does not override Kerberos configurations
- composer/WARN/2023\_002: Cloud Composer tasks are not interrupted by SIGKILL
- composer/WARN/2023\_003: Cloud Composer tasks are not failed due to resource pressure
- composer/WARN/2023\_004: Cloud Composer database CPU usage does not exceed 80%
- composer/WARN/2023\_005: Cloud Composer is consistently in healthy state
- composer/WARN/2023\_006: Airflow schedulers are healthy for the last hour
- composer/WARN/2023\_007: Cloud Composer Scheduler CPU limit exceeded
- composer/WARN/2023\_008: Cloud Composer Airflow database is in healthy state
- dataflow/ERR/2023\_001: Dataflow service account has dataflow.serviceAgent role
- dataflow/ERR/2023\_002: Dataflow job does not fail during execution due to IP space exhaustion
- dataflow/ERR/2023\_003: Dataflow job does not fail during execution due to incorrect subnet
- dataflow/ERR/2023\_004: Dataflow job does not fail due to organization policy constraints
- dataflow/ERR/2023\_005: Dataflow job does not fail during execution due credential or permission issue
- dataflow/ERR/2023\_006: Dataflow job fails if Private Google Access is disabled on subnetwork
- dataflow/WARN/2023\_001: Dataflow job does not have a hot key
- dataproc/ERR/2023\_002: No orphaned YARN application found
- dataproc/ERR/2023\_003: Dataproc cluster service account permissions
- dataproc/ERR/2023\_004: Dataproc firewall rules for connectivity between master and worker nodes
- dataproc/ERR/2023\_005: Dataproc cluster has sufficient quota
- dataproc/ERR/2023\_006: DataProc cluster user has networking permissions on host project
- gce/WARN/2023\_001: GCE snapshot policies are defined only for used disks
- gke/ERR/2023\_004: GKE ingresses are well configured
- gke/ERR/2023\_005: Workloads not reporting misconfigured CNI plugins
- iam/BP/2023\_001: Policy constraint 'AutomaticIamGrantsForDefaultServiceAccounts' enforced
- interconnect/BP/2023\_001: VLAN attachments deployed in same metro are in different EADs
- lb/BP/2023\_001: Cloud CDN is enabled on backends for global external load balancers
- notebooks/BP/2023\_001: Vertex AI Workbench instance enables system health report
- notebooks/BP/2023\_003: Vertex AI Workbench runtimes for managed notebooks are up to date
- notebooks/ERR/2023\_002: Vertex AI Workbench account has compute.subnetworks permissions
- notebooks/ERR/2023\_003: Vertex AI Workbench account has permissions to create and use notebooks
- notebooks/ERR/2023\_004: Vertex AI Workbench runtimes for managed notebooks are healthy
- notebooks/WARN/2023\_001: Vertex AI Workbench instance is not being OOMKilled
- notebooks/WARN/2023\_002: Vertex AI Workbench instance is in healthy data disk space status
- notebooks/WARN/2023\_003: Vertex AI Workbench instance is in healthy boot disk space status
- vpc/SEC/2023\_001: DNSSEC is enabled for public zones
- vpc/WARN/2023\_002: Private zone is attached to a VPC

#### Enhancements

- Support for sub project resource filtering (`--name`, `--location`, `--label`)
- Support fetching serial port output logs from Compute API (`--enable-gce-serial-buffer`)
- New product: Cloud Dataflow
- New product: Cloud Interconnect
- Add kubectl query module
- Optimizations for logging based composer rules

#### Fixes

- gke/BP/2022\_003: updated EOL schedule for GKE
- Fix billing project id not set at startup (github #58)
- Fix JSON format with --output=json (github #62)
- Fix GCS uniform bucket access detection (github #69)
- dataproc/WARN/2022\_002: fix attribute lookup error (github #57)
- gke/WARN/2021\_003: update GKE pod cidr rule to report values per pod cidr range

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
- composer/WARN/2022\_002: fluentd pods in Composer environments are not crashing
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
