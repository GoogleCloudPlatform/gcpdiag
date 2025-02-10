---
title: "gke/Ca Failed To Evict Pods"
linkTitle: "Ca Failed To Evict Pods"
weight: 3
type: docs
description: >
  Check for "scale.down.error.failed.to.evict.pods" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleDown event failed because some of the Pods could not be evicted from a node.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

Review best practices for Pod Disruption Budgets to ensure that the rules allow for eviction of application replicas
when acceptable.
https://cloud.google.com/architecture/best-practices-for-running-cost-effective-kubernetes-applications-on-gke#add-pod_disruption_budget-to-your-application

### Success Reason

No "scale.down.error.failed.to.evict.pods" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
