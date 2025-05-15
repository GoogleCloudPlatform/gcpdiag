---
title: "dataproc/Check Killing Orphaned Application"
linkTitle: "Check Killing Orphaned Application"
weight: 3
type: docs
description: >
  Verify if the killing of Orphaned applications has happened.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: COMPOSITE STEP

### Description

None

### Failure Reason

Log messages related to "{log}" were found on the cluster: {cluster_name}.

### Failure Remediation

To prevent orphaned YARN applications from being killed, set the cluster property `dataproc:dataproc.yarn.orphaned-app-termination.enable` to `false`.
More details are available in the documentation [1].
[1] <https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/cluster-properties>

### Success Reason

No log messages related to "{log}" were found on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
