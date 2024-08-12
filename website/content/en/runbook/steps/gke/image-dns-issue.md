---
title: "gke/Image Dns Issue"
linkTitle: "Image Dns Issue"
weight: 3
type: docs
description: >
  Node DNS sever cannot resolve the IP of the repository
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The DNS resolver (metadata server - 169.254.169.254:53) on the Node is unable to resolve the IP of the repository, preventing image pull. Check that the networking and DNS requirements mentioned in public documentation.
Example log entry that would help identify involved objects:
{LOG_ENTRY}

### Failure Remediation

Follow the documentation:
https://cloud.google.com/vpc/docs/configure-private-google-access#requirements

### Success Reason

No "Failed to pull image.*lookup.*server misbehaving" errors found between {START_TIME_UTC} and {END_TIME_UTC} UTC



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
