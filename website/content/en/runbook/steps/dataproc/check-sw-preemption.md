---
title: "dataproc/Check Sw Preemption"
linkTitle: "Check Sw Preemption"
weight: 3
type: docs
description: >
  Verify if secondary worker preemption has happened.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: COMPOSITE STEP

### Description

None

### Failure Reason

Found logs messages related to secondary worker preemption on the cluster: {cluster_name}.

### Failure Remediation

This error occurs when secondary nodes are preempted.
Please confirm if you are using secondary workers with preemptible instances. (The default Dataproc secondary worker type is a standard preemptible VM.)

You can recreate a cluster configured with non-preemptible secondary workers to ensure the secondary workers are not preemptible.
[1] <https://cloud.google.com/dataproc/docs/concepts/compute/secondary-vms#non-preemptible_workers>

### Success Reason

Didn't find logs messages related to secondary worker preemption on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
