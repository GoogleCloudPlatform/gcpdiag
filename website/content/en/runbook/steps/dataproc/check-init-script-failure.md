---
title: "dataproc/Check Init Script Failure"
linkTitle: "Check Init Script Failure"
weight: 3
type: docs
description: >
  Verify if dataproc cluster init script failed.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

The initialization action provided during cluster creation failed to install.

### Failure Reason

The cluster {cluster_name} creation failed because the initialization script encountered an error.

### Failure Remediation

A Dataproc cluster initialization script failure means that a script intended to run during the cluster's setup did not complete successfully.
To resolve this issue:

- Review initialization actions considerations and guidelines [1].
- Examine the output logs. The error message should provide a link to the logs in Cloud Storage.
[1]<https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/init-actions#important_considerations_and_guidelines>

### Success Reason

The initialization actions for cluster {cluster_name} in project {project_id} completed successfully without errors.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
