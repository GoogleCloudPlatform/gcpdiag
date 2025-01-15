---
title: "gke/Resource Quota Exceeded"
linkTitle: "Resource Quota Exceeded"
weight: 3
type: docs
description: >
  Verifies that Kubernetes resource quotas have been exceeded or not.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The cluster {CLUSTER} in location {LOCATION} in project {PROJECT} has exceeded its kubernetes resource quota between {START_TIME_UTC} and {END_TIME_UTC} UTC.
Example log entry that would help identify involved objects:

{LOG_ENTRY}

### Failure Remediation

For clusters with under 100 nodes, GKE applies Kubernetes resource quota to every namespace. These quotas protect the cluster's control plane from instability caused by potential bugs in applications deployed to the cluster. You cannot remove these quotas because they are enforced by GKE.
See details: https://cloud.google.com/kubernetes-engine/quotas#resource_quotas
You can use below command to list resourcequota in your cluster.

`kubectl get resourcequota --all-namespaces`

Refer document to know more about resource quota: https://kubernetes.io/docs/concepts/policy/resource-quotas/

There are two resolutions for this issues regarding GKE resource quotas with name "gke-resource-quotas". Kindly open the GCP support case to increase a resource quota to a specific number or request to disable GKE resource quotas for the cluster.

### Success Reason

The cluster {CLUSTER} in location {LOCATION} in project {PROJECT} was within its kubernetes resource quota between {START_TIME_UTC} and {END_TIME_UTC} UTC.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->