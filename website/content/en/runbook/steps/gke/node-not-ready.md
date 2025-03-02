---
title: "gke/Node Not Ready"
linkTitle: "Node Not Ready"
weight: 3
type: docs
description: >
  Checks if nodes have been in NotReady status for an extended period (e.g., 10 minutes).
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The node {node} was auto-repaired because it was in a NotReady state for more than approximately 10 minutes.

### Failure Remediation

The auto-repair should have fixed the detected NotReady state.
For more details check: <https://cloud.google.com/kubernetes-engine/docs/how-to/node-auto-repair>

### Success Reason

The node {node} was auto-repaired for reasons other than being in a NotReady state.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
