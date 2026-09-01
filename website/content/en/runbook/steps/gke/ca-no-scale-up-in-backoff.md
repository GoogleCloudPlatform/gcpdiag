---
title: "gke/Ca No Scale Up In Backoff"
linkTitle: "Ca No Scale Up In Backoff"
weight: 3
type: docs
description: >
  Check for "no.scale.up.in.backoff" logs representing MIGs in backoff
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleUp event was skipped because one or more node pools (MIGs) are in backoff state due to previous node bootstrapping or provisioning failures.
List of node groups in backoff:
{backoff_details}

### Failure Remediation

When a node pool fails to bootstrap (e.g. because of networking, service account, or image issues), the Cluster Autoscaler enters a backoff period before trying to scale it up again.
Check the GKE system events or GCE compute engine operation logs for the instance creation failures to resolve the root bootstrapping issue.
For details, see: <https://cloud.google.com/kubernetes-engine/docs/troubleshooting/cluster-autoscaler-scale-up>

### Success Reason

No "no.scale.up.in.backoff" logs found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
