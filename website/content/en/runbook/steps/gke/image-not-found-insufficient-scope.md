---
title: "gke/Image Not Found Insufficient Scope"
linkTitle: "Image Not Found Insufficient Scope"
weight: 3
type: docs
description: >
  Check for Image not found log entries with insufficient_scope server message
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Either user or service account that's trying to pull the image doesn't have the necessary permissions to access it or
Image doesn't exist.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation


1. Verify that the image name is correct.
2. Ensure the node's service account has the necessary permissions. Refer to the documentation:
<https://cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads#image-not-found>

### Success Reason

No "Failed to pull image.*insufficient_scope" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
