---
title: "dataproc/Check Cluster Quota"
linkTitle: "Check Cluster Quota"
weight: 3
type: docs
description: >
  Verify if the Dataproc cluster has quota issues.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: START

### Description

Checks if the Dataproc cluster had creation issues due to quota.

### Failure Reason

The cluster {cluster_name} in project {project_id} could not be created due to insufficient quota in the project.

### Failure Remediation

This issue occurs when the requested Dataproc cluster exceeds the project's available quota for resources such as CPU, disk space, or IP addresses.
To resolve this issue:

- Request additional quota [1] via the Google Cloud console.
- Create the cluster in a different project.
[1] <https://cloud.google.com/docs/quotas/view-manage#managing_your_quota_console>

### Success Reason

No issues with insufficient quota identified for cluster {cluster_name} in project {project_id}. If the intended cluster does not appear in the Dataproc UI, verify the provided cluster_name parameter.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
