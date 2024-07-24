---
title: "gke/Unallocatable Tpu"
linkTitle: "Unallocatable Tpu"
weight: 3
type: docs
description: >
  Checks TPU allocation
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The node {NODE} was auto-repaired because it had unallocatable TPU(s) for more than 10 minutes.

### Failure Remediation

The auto-repair should have fixed the detected unallocatable TPU(s).
For more details check: https://cloud.google.com/kubernetes-engine/docs/how-to/tpus#node-auto-repair

### Success Reason

The node {NODE} was auto-repaired for reasons other than unallocatable TPU(s).



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
