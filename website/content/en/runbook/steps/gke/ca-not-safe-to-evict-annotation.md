---
title: "gke/Ca Not Safe To Evict Annotation"
linkTitle: "Ca Not Safe To Evict Annotation"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.pod.not.safe.to.evict.annotation" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleDown event failed because a Pod on the node has the safe-to-evict=false annotation
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

If the Pod can be safely evicted, edit the manifest of the Pod and update the annotation to
"cluster-autoscaler.kubernetes.io/safe-to-evict": "true".

### Success Reason

No "no.scale.down.node.pod.not.safe.to.evict.annotation" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
