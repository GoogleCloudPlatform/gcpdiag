---
title: "pubsub/Check Service Account Permissions"
linkTitle: "Check Service Account Permissions"
weight: 3
type: docs
description: >
  Checks if the Pub/Sub service account has correct permissions on the bucket.
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)\
**Step Type**: AUTOMATED STEP

### Description

This step checks if the Pub/Sub service account has correct permissions on the bucket

### Failure Reason

Pub/Sub service account '{service_account}' is MISSING permission on bucket '{bucket_name}'
### Failure Remediation

Grant the Pub/Sub service account '{service_account}' at least the storage.objects.create and storage.buckets.get permissions on the bucket '{bucket_name}'.


<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
