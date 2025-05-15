---
title: "gke/Image Not Found"
linkTitle: "Image Not Found"
weight: 3
type: docs
description: >
  Check for Image not found log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

A container on pod on node failed to pull image because the image was not found in the repository.
Example log entry:

{log_entry}

### Failure Remediation

Refer to the troubleshooting documentation:
<https://cloud.google.com/kubernetes-engine/docs/troubleshooting#ImagePullBackOff>

### Success Reason

No "Failed to pull image.*not found" errors were found for cluster between {start_time} and {end_time}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
