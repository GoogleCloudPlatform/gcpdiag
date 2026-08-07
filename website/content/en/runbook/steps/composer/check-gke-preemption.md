---
title: "composer/Check Gke Preemption"
linkTitle: "Check Gke Preemption"
weight: 3
type: docs
description: >
  Check if worker pods were preempted by GKE.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This check verifies if there are any worker pods were preempted by GKE.

### Failure Reason

GKE Preemption found in Logs.

### Failure Remediation

Enable task retries in the DAG OR contact Google Cloud Support.

### Success Reason

No GKE Preemption found in Logs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
