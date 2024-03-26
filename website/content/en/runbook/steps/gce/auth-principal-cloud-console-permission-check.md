<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
---
title: "gce/Auth Principal Cloud Console Permission Check"
linkTitle: "Auth Principal Cloud Console Permission Check"
weight: 3
type: docs
description: >
  Validates if the user has the 'compute.projects.get' permission within the GCP Project.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This permission is essential to be able to use SSH in browser and
  viewing the Compute Engine resources in the Cloud Console.

### Failure Reason

To access Compute Engine via the Google Cloud console (i.e. SSH-in-browser),
the user must have "compute.projects.get" permission.

### Failure Remediation

Review the permissions guide for accessing Compute Engine resources:
https://cloud.google.com/compute/docs/access/iam#console_permission

### Success Reason

The user is authorized to view the Google Cloud console which will allow SSH-in-browser use case



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
