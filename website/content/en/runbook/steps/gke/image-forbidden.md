---
title: "gke/Image Forbidden"
linkTitle: "Image Forbidden"
weight: 3
type: docs
description: >
  Image cannot be pulled, insufficiente permissions
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Image cannot be pulled by a container on Pod, because there are not enough permissions to pull it from the repository. Verify the node SA has the correct permissions.
Example log entry that would help identify involved objects:

{LOG_ENTRY}

### Failure Remediation

Follow the documentation:
https://cloud.google.com/artifact-registry/docs/integrate-gke#permissions

### Success Reason

No "Failed to pull image.*403 Forbidden" errors found between {START_TIME_UTC} and {END_TIME_UTC} UTC



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
