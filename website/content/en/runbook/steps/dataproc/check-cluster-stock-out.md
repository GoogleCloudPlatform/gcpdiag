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

Dataproc cluster stockout occurs when there are insufficient resources available in a specific zone or region to create your requested cluster.
Solutions to resolve the issue include:

- Create the cluster in a different zone or region.
- Use the Dataproc Auto Zone placement feature by not specifying the zone [1].
[1] <https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/auto-zone>

### Success Reason

No issues with stockouts and insufficient resources in project {project_id} has been identified for {cluster_name}, please double-check if you have provided
the right cluster_name parameter if the cluster you are trying to create doesn't appear in Dataproc UI.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
