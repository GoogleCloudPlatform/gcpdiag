---
title: "gke/Resource Quota Exceeded"
linkTitle: "Resource Quota Exceeded"
weight: 3
type: docs
description: >
  Verify that Kubernetes resource quotas have not been exceeded.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The cluster projects/{project}/locations/{location}/clusters/{cluster} has exceeded its Kubernetes resource quota between
{start_time} and {end_time}.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

For clusters with under 100 nodes, GKE applies a Kubernetes resource quota to every namespace. These quotas protect the
cluster's control plane from instability caused by potential bugs in applications deployed to the cluster. These quotas cannot
be removed because they are enforced by GKE.
See details: <https://cloud.google.com/kubernetes-engine/quotas#resource_quotas>
To list resource quotas in the cluster, use the following command:

`kubectl get resourcequota --all-namespaces`

Refer to the Kubernetes documentation for more information about resource quotas: <https://kubernetes.io/docs/concepts/policy/resource-quotas/>

For the GKE resource quotas named "gke-resource-quotas", open a
GCP support case to request either an increase to a specific quota limit or the disabling of GKE resource quotas for the
cluster.

### Success Reason

The cluster projects/{project}/locations/{location}/clusters/{cluster} was within its Kubernetes resource quota between
{start_time} and {end_time}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
