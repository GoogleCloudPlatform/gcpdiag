---
title: "dataproc/Check Cluster Stock Out"
linkTitle: "Check Cluster Stock Out"
weight: 3
type: docs
description: >
  Verify if Dataproc cluster has stockout issue.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

Checks if the zone being used to create the cluster has sufficient resources.

### Failure Reason

The cluster {cluster_name} creation in project {project_id} failed due to insufficient resources in the selected zone/region.

### Failure Remediation

Dataproc cluster stockout occurs when there are insufficient resources available in a specific zone or region to create the requested cluster.
To resolve this issue:

- Create the cluster in a different zone or region.
- Use the Dataproc Auto Zone placement feature by not specifying the zone [1].
[1] <https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/auto-zone>

### Success Reason

No issues with stockouts identified for cluster {cluster_name} in project {project_id}. If the intended cluster does not appear in the Dataproc UI, verify the provided cluster_name parameter.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
