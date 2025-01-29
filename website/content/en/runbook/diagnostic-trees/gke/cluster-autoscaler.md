---
title: "gke/Cluster Autoscaler"
linkTitle: "gke/cluster-autoscaler"
weight: 3
type: docs
description: >
  Analyses logs in the project where the cluster is running.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

If there are log entries that contain messages listed in the public documentation
  https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-autoscaler-visibility#messages
  then provide details on how each particular issue can be solved.

  The following ScaleUP logs messages are covered:
  - scale.up.error.out.of.resources
  - scale.up.error.quota.exceeded
  - scale.up.error.waiting.for.instances.timeout
  - scale.up.error.ip.space.exhausted
  - scale.up.error.service.account.deleted

  The following ScaleDown logs messages are covered:
  - scale.down.error.failed.to.evict.pods
  - no.scale.down.node.node.group.min.size.reached
  - no.scale.down.node.scale.down.disabled.annotation
  - no.scale.down.node.minimal.resource.limits.exceeded
  - no.scale.down.node.no.place.to.move.pods
  - no.scale.down.node.pod.not.backed.by.controller
  - no.scale.down.node.pod.not.safe.to.evict.annotation
  - no.scale.down.node.pod.kube.system.unmovable
  - no.scale.down.node.pod.not.enough.pdb
  - no.scale.down.node.pod.controller.not.found
  - no.scale.down.node.pod.unexpected.error

### Executing this runbook

```shell
gcpdiag runbook gke/cluster-autoscaler \
  -p project_id=value \
  -p name=value \
  -p location=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The ID of the project hosting the GKE Cluster |
| `name` | False | None | str | (Optional) The name of the GKE cluster, to limit search only for this cluster |
| `location` | False | None | str | The zone or region of the GKE cluster |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Cluster Autoscaler Start](/runbook/steps/gke/cluster-autoscaler-start)

  - [Ca Out Of Resources](/runbook/steps/gke/ca-out-of-resources)

  - [Ca Quota Exceeded](/runbook/steps/gke/ca-quota-exceeded)

  - [Ca Instance Timeout](/runbook/steps/gke/ca-instance-timeout)

  - [Ca Ip Space Exhausted](/runbook/steps/gke/ca-ip-space-exhausted)

  - [Ca Service Account Deleted](/runbook/steps/gke/ca-service-account-deleted)

  - [Ca Min Size Reached](/runbook/steps/gke/ca-min-size-reached)

  - [Ca Failed To Evict Pods](/runbook/steps/gke/ca-failed-to-evict-pods)

  - [Ca Disabled Annotation](/runbook/steps/gke/ca-disabled-annotation)

  - [Ca Min Resource Limit Exceeded](/runbook/steps/gke/ca-min-resource-limit-exceeded)

  - [Ca No Place To Move Pods](/runbook/steps/gke/ca-no-place-to-move-pods)

  - [Ca Pods Not Backed By Controller](/runbook/steps/gke/ca-pods-not-backed-by-controller)

  - [Ca Not Safe To Evict Annotation](/runbook/steps/gke/ca-not-safe-to-evict-annotation)

  - [Ca Pod Kube System Unmovable](/runbook/steps/gke/ca-pod-kube-system-unmovable)

  - [Ca Pod Not Enough Pdb](/runbook/steps/gke/ca-pod-not-enough-pdb)

  - [Ca Pod Controller Not Found](/runbook/steps/gke/ca-pod-controller-not-found)

  - [Ca Pod Unexpected Error](/runbook/steps/gke/ca-pod-unexpected-error)

  - [Cluster Autoscaler End](/runbook/steps/gke/cluster-autoscaler-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
