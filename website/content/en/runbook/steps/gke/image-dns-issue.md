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

The DNS resolver (metadata server 169.254.169.254:53) on node was unable to resolve the image repository's IP address, preventing image pull. This often indicates issues with networking or DNS configuration.
Example log entry:

{log_entry}

### Failure Remediation

Verify networking and DNS requirements, particularly for Private Google Access. Refer to the documentation:
<https://cloud.google.com/vpc/docs/configure-private-google-access#requirements>

### Success Reason

No "Failed to pull image.*lookup.*server misbehaving" errors were found for cluster between {start_time} and {end_time}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
