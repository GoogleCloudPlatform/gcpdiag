# gcpdiag - Diagnostics for Google Cloud Platform

[![code analysis badge](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/code-analysis.yml/badge.svg?branch=main&event=push)](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/code-analysis.yml?query=branch%3Amain+event%3Apush)
[![test badge](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/GoogleCloudPlatform/gcpdiag/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)

**gcpdiag** is a command-line diagnostics tool for GCP customers. It finds
and helps to fix common issues in Google Cloud Platform projects. It is used to
test projects against a wide range of best-practices and frequent mistakes,
based on the troubleshooting experience of the Google Cloud Support team.

gcpdiag is open-source and contributions are welcome! Note that this is not
an officially supported Google product, but a community effort. The Google Cloud
Support team maintains this code and we do our best to avoid causing any
problems in your projects, but we give no guarantees to that end.

<img src="docs/gcpdiag-demo-2021-10-01.gif" alt="gcpdiag demo" width="800"/>

## Installation

You can run gcpdiag using a shell wrapper that starts gcpdiag in a Docker
container. This should work on any machine with Docker installed, including
Cloud Shell.

```
curl https://gcpdiag.dev/gcpdiag.sh >gcpdiag
chmod +x gcpdiag
gcloud auth login --update-adc
./gcpdiag lint --auth-adc --project=MYPROJECT
```

Note: the `gcloud auth` step is not required in Cloud Shell.

## Usage

Currently gcpdiag mainly supports one subcommand: `lint`, which is used
to run diagnostics on one or more GCP projects.

```
usage: gcpdiag lint --project P [OPTIONS]

Run diagnostics in GCP projects.

optional arguments:
  -h, --help           show this help message and exit
  --auth-adc           Authenticate using Application Default Credentials
  --auth-key FILE      Authenticate using a service account private key file
  --auth-oauth         Authenticate using Oauth user authentication (default, except in Cloud Shell)
  --project P          Project ID of project to inspect
  --billing-project P  Project used for billing/quota of API calls done by gcpdiag
                       (default is the inspected project, requires 'serviceusage.services.use' permission)
  --show-skipped       Show skipped rules
  --hide-ok            Hide rules with result OK
  -v, --verbose        Increase log verbosity
  --within-days D      How far back to search logs and metrics (default: 3)
```

### Authentication

gcpdiag supports authentication using multiple mechanisms:

1. Oauth user consent flow

   By default gcpdiag can use a Oauth user authentication flow, similarly to
   what gcloud does. It will print a URL that you need to access with a browser,
   and ask you to enter the token that you receive after you authenticate there.
   Note that this currently doesn't work for people outside of google.com,
   because gcpdiag is not approved for external Oauth authentication yet.

   The credentials will be cached on disk, so that you can keep running it for 1
   hour. To remove cached authentication credentials, you can delete the
   `$HOME/.cache/gcpdiag` directory.

1. Application default credentials

   If you supply `--auth-adc`, gcpdiag will use [Application Default
   Credentials](https://google-auth.readthedocs.io/en/latest/reference/google.auth.html#google.auth.default)
   to authenticate. For example this works out of the box in Cloud Shell and
   you don't need to re-authenticate, or you can use `gcloud auth login
   --update-adc` to refresh the credentials using gcloud.

1. Service account key

   You can also use the `--auth-key` parameter to specify the [private
   key](https://cloud.google.com/iam/docs/creating-managing-service-account-keys)
   of a service account.

The authenticated user will need as minimum the following roles granted (both of them):

- `Viewer` on the inspected project
- `Service Usage Consumer` on the project used for billing/quota enforcement,
  which is per default the project being inspected, but can be explicitely set
  using the `--billing-project` option

The Editor and Owner roles include all the required permissions, but we
recommend that if you use service account authentication (`--auth-key`), you
only grant the Viewer+Service Usage Consumer on that service account.

### Test Products, Classes, and IDs

Tests are organized by product, class, and ID.

The **product** is the GCP service that is being tested. Examples: GKE or GCE.

The **class** is what kind of test it is, currently we have:

Class name | Description
---------- | -----------------------------------------------
BP         | Best practice, opinionated recommendations
WARN       | Warnings: things that are possibly wrong
ERR        | Errors: things that are very likely to be wrong
SEC        | Potential security issues

The **ID** is currently formatted as YYYY_NNN, where YYYY is the year the test
was written, and NNN is a counter. The ID must be unique per product/class
combination.

Each test also has a **short_description** and a **long_description**. The short
description is a statement about the **good state** that is being verified to be
true (i.e. we don't test for errors, we test for compliance, i.e. an problem not
to be present).

### Available Rules

Product | Class | ID       | Short description                                            | Long description
------- | ----- | -------- | ------------------------------------------------------------ | --------------------
gce     | BP    | 2021_001 | Serial port logging is enabled.                              | Serial port output can be often useful for troubleshooting, and enabling serial logging makes sure that you don't lose the information when the VM is restarted. Additionally, serial port logs are timestamped, which is useful to determine when a particular serial output line was printed.  Reference:   https://cloud.google.com/compute/docs/instances/viewing-serial-port-output
gce     | ERR   | 2021_001 | Managed instance groups are not reporting scaleup failures.  | Suggested Cloud Logging query: resource.type="gce_instance" AND log_id(cloudaudit.googleapis.com/activity) AND severity=ERROR AND protoPayload.methodName="v1.compute.instances.insert" AND protoPayload.requestMetadata.callerSuppliedUserAgent="GCE Managed Instance Group"
gce     | ERR   | 2021_002 | OS Config permissions check for a project                    | The metadata of OS Config enabled should be present at the project level or instance level. Secondly every vm should have minimally a service account attached to the vm. Lastly the Google managed service account should have the role roles/osconfig.serviceAgent as a permission
gce     | ERR   | 2021_003 | Google APIs service agent has Editor role.                   | The Google API service agent project-number@cloudservices.gserviceaccount.com runs internal Google processes on your behalf. It is automatically granted the Editor role on the project.  Reference: https://cloud.google.com/iam/docs/service-accounts#google-managed
gce     | WARN  | 2021_001 | GCE instance service account permissions for logging.        | The service account used by GCE instance should have the logging.logWriter permission, otherwise, if you install the logging agent, it won't be able to send the logs to Cloud Logging.
gce     | WARN  | 2021_002 | GCE nodes have good disk performance.                        | Verify that the persistent disks used by the GCE instances provide a "good" performance, where good is defined to be less than 100ms IO queue time. If it's more than that, it probably means that the instance would benefit from a faster disk (changing the type or making it larger).
gke     | BP    | 2021_001 | GKE system logging and monitoring enabled.                   | Disabling system logging and monitoring (aka "GKE Cloud Operations") severly impacts the ability of Google Cloud Support to troubleshoot any issues that you might have.
gke     | ERR   | 2021_001 | GKE nodes service account permissions for logging.           | The service account used by GKE nodes should have the logging.logWriter role, otherwise ingestion of logs won't work.
gke     | ERR   | 2021_002 | GKE nodes service account permissions for monitoring.        | The service account used by GKE nodes should have the monitoring.metricWriter role, otherwise ingestion of metrics won't work.
gke     | ERR   | 2021_003 | App-layer secrets encryption is activated and Cloud KMS key is enabled. | GKE's default service account cannot use a disabled Cloud KMS key for application-level secrets encryption.
gke     | ERR   | 2021_004 | GKE nodes aren't reporting connection issues to apiserver.   | GKE nodes need to connect to the control plane to register and to report status regularly. If connection errors are found in the logs, possibly there is a connectivity issue, like a firewall rule blocking access.  The following log line is searched: "Failed to connect to apiserver"
gke     | ERR   | 2021_005 | GKE nodes aren't reporting connection issues to storage.google.com. | GKE node need to download artifacts from storage.google.com:443 when booting. If a node reports that it can't connect to storage.google.com, it probably means that it can't boot correctly.  The following log line is searched in the GCE serial logs: "Failed to connect to storage.googleapis.com"
gke     | ERR   | 2021_006 | GKE Autoscaler isn't reporting scaleup failures.             | If the GKE autoscaler reported a problem when trying to add nodes to a cluster, it could mean that you don't have enough resources to accomodate for new nodes. E.g. you might not have enough free IP addresses in the GKE cluster network.  Suggested Cloud Logging query: resource.type="gce_instance" AND log_id(cloudaudit.googleapis.com/activity) AND severity=ERROR AND protoPayload.methodName="v1.compute.instances.insert" AND protoPayload.requestMetadata.callerSuppliedUserAgent="GCE Managed Instance Group for GKE"
gke     | ERR   | 2021_007 | GKE service account permissions.                             | Verifying if Google Kubernetes Engine service account is created and assigned the Kubernetes Engine Service Agent role on the project. See also: https://cloud.google.com/kubernetes-engine/docs/troubleshooting#gke_service_account_deleted
gke     | ERR   | 2021_008 | Google APIs service agent has Editor role.                   | The Google API service agent project-number@cloudservices.gserviceaccount.com runs internal Google processes on your behalf. It is automatically granted the Editor role on the project.  Reference: https://cloud.google.com/iam/docs/service-accounts#google-managed
gke     | ERR   | 2021_009 | Node pool service account exists and not disabled            | Disabling or deleting the service account used by a node pool will render the node pool not functional. To fix - restore the default compute account or service account that was specified when the node pool was created.
gke     | SEC   | 2021_001 | GKE nodes don't use the GCE default service account.         | The GCE default service account has more permissions than are required to run your Kubernetes Engine cluster. You should either use GKE Workload Identity or create and use a minimally privileged service account.  Reference: Hardening your cluster's security   https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster#use_least_privilege_sa
gke     | WARN  | 2021_001 | GKE master version available for new clusters.               | The GKE master version should be a version that is available for new clusters. If a version is not available it could mean that it is deprecated, or possibly retired due to issues with it.
gke     | WARN  | 2021_002 | GKE nodes version available for new clusters.                | The GKE nodes version should be a version that is available for new clusters. If a version is not available it could mean that it is deprecated, or possibly retired due to issues with it.
gke     | WARN  | 2021_003 | GKE cluster size close to maximum allowed by pod range       | The maximum amount of nodes in a GKE cluster is limited based on its pod CIDR range. This test checks if the cluster is approaching the maximum amount of nodes allowed by the pod range. Users may end up blocked in production if they are not able to scale their cluster due to this hard limit imposed by the pod CIDR.
gke     | WARN  | 2021_004 | GKE system workloads are running stable.                     | GKE includes some system workloads running in the user-managed nodes which are essential for the correct operation of the cluster. We verify that restart count of containers in one of the system namespaces (kube-system, istio-system, custom-metrics) stayed stable in the last 24 hours.
gke     | WARN  | 2021_005 | GKE nodes have good disk performance.                        | Disk performance is essential for the proper operation of GKE nodes. If too much IO is done and the disk latency gets too high, system components can start to misbehave. Often the boot disk is a bottleneck because it is used for multiple things: the operating system, docker images, container filesystems (usually including /tmp, etc.), and EmptyDir volumes.
gke     | WARN  | 2021_006 | GKE nodes aren't reporting conntrack issues.                 | The following string was found in the serial logs: nf_conntrack: table full  See also: https://cloud.google.com/kubernetes-engine/docs/troubleshooting
gke     | WARN  | 2021_007 | GKE nodes have enough free space on the boot disk.           | GKE nodes need free space on their boot disks to be able to function properly. If /var is getting full, it might be because logs are not being rotated correctly, or maybe a container is creating too much data in the overlayfs.
gke     | WARN  | 2021_008 | Istio/ASM version not deprecated nor close to deprecation in GKE | As of GKE 1.22, all Istio versions below 1.10.0 and ASM versions of 1.10.2 and below will no longer work. We recommend upgrading to ASM Managed Control Plane or version 1.10.3+ to avoid outages. Please find more details about this in https://github.com/istio/istio/issues/34665. For Support status of Istio releases, please see: https://istio.io/latest/docs/releases/supported-releases/#support-status-of-istio-releases
iam     | SEC   | 2021_001 | No service accounts have the Owner role                      | A Service account should not have a role that could potentially increase the security risk to the project to malicious activity. See also: https://cloud.google.com/iam/docs/best-practices-for-securing-service-accounts
