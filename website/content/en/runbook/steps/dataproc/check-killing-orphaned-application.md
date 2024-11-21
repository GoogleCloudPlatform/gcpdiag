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

Found logs messages related to "{log}" on the cluster: {cluster_name}.

### Failure Remediation

Please set dataproc:dataproc.yarn.orphaned-app-termination.enable to false if you don't want to kill orphaned yarn application.
You can find more details in the documentation [1].
[1] https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/cluster-properties

### Success Reason

Didn't find logs messages related to "{log}" on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
