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

Didn't identify any user specified Cloud Storage connector version. The cluster is using the default version.

### Uncertain Reason

Identified a user specified Cloud Storage connector version. Please have in mind that all Dataproc clusters have pre-installed GCS connector.
If your application doesn't depend on a non-default connector version we would recommend to not specify one.
<https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters#supported-dataproc-image-versions>

### Uncertain Remediation

If you would like to use the non-default connector make sure that the setup has been done correctly following:
<https://cloud.google.com/dataproc/docs/concepts/connectors/cloud-storage#non-default_connector_versions>
<https://cloud.google.com/dataproc/docs/concepts/connectors/cloud-storage#service_account_permissions>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
