---
title: "gke/Ca Pod Controller Not Found"
linkTitle: "Ca Pod Controller Not Found"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.pod.controller.not.found" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Pod is blocking the ScaleDown event because its controller (for example, a Deployment or ReplicaSet) can't be found.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

To determine what actions were taken that left the Pod running after its controller was removed, review the logs. To
resolve this issue, manually delete the Pod.

### Success Reason

No "no.scale.down.node.pod.controller.not.found" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
