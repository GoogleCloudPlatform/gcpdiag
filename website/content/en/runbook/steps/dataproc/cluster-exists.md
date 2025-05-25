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

Cluster {cluster_name} does not exist in project {project_id}

### Failure Remediation

Create the cluster again and keep it in the ERROR state in the Dataproc UI, or manually provide additional parameters using the gcpdiag command:

`gcpdiag runbook dataproc/cluster-creation -p cluster_name=CLUSTER_NAME -p cluster_uuid=CLUSTER_UUID -p network=NETWORK_URI -p subnetwork=SUBNETWORK_URI -p service_account=SERVICE_ACCOUNT -p internal_ip_only=True/False --project=PROJECT_ID`

Refer to <https://gcpdiag.dev/runbook/diagnostic-trees/dataproc/> for guidance on specifying additional parameters.

### Success Reason

Cluster {cluster_name} exists in project {project_id}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
