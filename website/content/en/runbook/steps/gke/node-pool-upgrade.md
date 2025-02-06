---
title: "gke/Node Pool Upgrade"
linkTitle: "Node Pool Upgrade"
weight: 3
type: docs
description: >
  Checks if the node was removed by Cluster Upgrade Operation.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The node {node} was unavailable due to a node pool upgrade.

### Failure Remediation

This is expected behavior, when the upgrade is performed, nodes are drained and re-created to match the desired version.

To list the node upgrade operations, please issue the following gcloud command:

gcloud container operations list --filter=operationType:UPGRADE_NODES

For more details about node upgrades please consult the documentation:
https://cloud.google.com/kubernetes-engine/docs/how-to/node-auto-upgrades

### Success Reason

The node {node} was unavailable for reasons other than a node pool upgrade.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
