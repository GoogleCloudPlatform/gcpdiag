---
title: "dataproc/Cluster Exists"
linkTitle: "Cluster Exists"
weight: 3
type: docs
description: >
  Prepares the parameters required for the dataproc/cluster-creation runbook.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

Ensures both project_id and cluster_name parameters are available.

### Failure Reason

Cluster {cluster_name} does not exists in project {project_id}

### Failure Remediation

Either create again the cluster and keep it in ERROR state in Dataproc UI or manually provide additional parameters using command:

`gcpdiag runbook dataproc/cluster-creation -p cluster_name=CLUSTER_NAME -p cluster_uuid=CLUSTER_UUID -p network=NETWORK_URI -p subnetwork=SUBNETWORK_URI -p service_account=SERVICE_ACCOUNT -p internal_ip_only=True/False --project=PROJECT_ID`

Please visit <https://gcpdiag.dev/runbook/diagnostic-trees/dataproc/> for any additional parameters you would like to specify.

### Success Reason

Cluster {cluster_name} exists in project {project_id}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
