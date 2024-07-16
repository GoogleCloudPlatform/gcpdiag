---
title: "gce/Preemptible Instance"
linkTitle: "Preemptible Instance"
weight: 3
type: docs
description: >
  Investigate the cause of a preemptible VM termination
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

Preemptible VMs are short-lived instances. This step investigates normal or abnormal
  circumstances leading to termination.

### Failure Reason

{status_message}

### Failure Remediation

Instance {full_resource_path} were preempted as part of a spot VM normal process.

Spot VMs have significant discounts, but Compute Engine might preemptively stop or delete
(preempt) Spot VMs to reclaim capacity at any time.

Read more on here the preemption process occurs here [1][2]

This is a normal process and no action is required.

[1] <https://cloud.google.com/compute/docs/instances/spot#preemption>
[2] <https://cloud.google.com/compute/docs/instances/spot>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
