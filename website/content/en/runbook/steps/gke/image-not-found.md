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

Image cannot be pulled by a container on Pod, because the image is not found on the repository.
Check if the image is correctly written or if it exists in the repository.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

Follow the documentation:
https://cloud.google.com/kubernetes-engine/docs/troubleshooting#ImagePullBackOff

### Success Reason

No "Failed to pull image.*not found" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
