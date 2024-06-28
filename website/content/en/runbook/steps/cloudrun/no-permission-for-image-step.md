---
title: "cloudrun/No Permission For Image Step"
linkTitle: "No Permission For Image Step"
weight: 3
type: docs
description: >
  Checks if Cloud Run service agent can fetch the image.
---

**Product**: [Cloud Run](https://cloud.google.com/run)\
**Step Type**: AUTOMATED STEP

### Description

This step will check if the error is present and link to additional troubleshooting steps.

### Failure Reason

Cloud Run Service agent {sa} does not have permissions to read image {image}.

### Failure Remediation

Please make sure that {sa} has roles/storage.objectViewer role if the image is stored in Container
Registry or roles/artifactregistry.reader if in Artifact Registry. Please note that the role needs to be granted in the
project where the image is stored.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
