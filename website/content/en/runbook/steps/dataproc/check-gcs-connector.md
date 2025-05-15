---
title: "dataproc/Check Gcs Connector"
linkTitle: "Check Gcs Connector"
weight: 3
type: docs
description: >
  Check for non-default GCS connector and for errors in logs connected to Cloud Storage.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: COMPOSITE STEP

### Description

None

### Success Reason

No user-specified Cloud Storage connector version was identified. The cluster is using the default version.

### Uncertain Reason

A user-specified Cloud Storage connector version was identified for cluster. Using a non-default connector version can lead to issues if not required by the application, as Dataproc clusters include a default pre-installed GCS connector.
<https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters#supported-dataproc-image-versions>

### Uncertain Remediation

Verify the setup is correct if using a non-default Cloud Storage connector by following:
<https://cloud.google.com/dataproc/docs/concepts/connectors/cloud-storage#non-default_connector_versions>
<https://cloud.google.com/dataproc/docs/concepts/connectors/cloud-storage#service_account_permissions>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
