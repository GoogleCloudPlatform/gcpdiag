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

Grant {sa} the roles/storage.objectViewer role if the image is stored in Container Registry or the roles/artifactregistry.reader role if in Artifact Registry. Note that the role must be granted in the project where the image is stored.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
