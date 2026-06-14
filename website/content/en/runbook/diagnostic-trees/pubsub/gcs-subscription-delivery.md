---
title: "pubsub/Gcs Subscription Delivery"
linkTitle: "pubsub/gcs-subscription-delivery"
weight: 3
type: docs
description: >
  Troubleshoot Pub/Sub to Cloud Storage subscription issues.
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)
**Kind**: Debugging Tree

### Description

This runbook checks for common configuration problems with Pub/Sub subscriptions
  that are set up to write directly to a Google Cloud Storage bucket.

  Checks performed:
  - Subscription existence and type.
  - Cloud Storage bucket existence.
  - IAM permissions for the Pub/Sub service account on the bucket.
  - State of the Pub/Sub subscription.

### Executing this runbook

```shell
gcpdiag runbook pubsub/gcs-subscription-delivery \
  -p project_id=value \
  -p subscription_name=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID containing the Pub/Sub subscription |
| `subscription_name` | True | None | str | The Pub/Sub subscription ID |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Gcs Subscription Delivery Start](/runbook/steps/pubsub/gcs-subscription-delivery-start)

  - [Gcs Subscription Existence Check](/runbook/steps/pubsub/gcs-subscription-existence-check)

  - [Check Gcs Bucket](/runbook/steps/pubsub/check-gcs-bucket)

  - [Check Service Account Permissions](/runbook/steps/pubsub/check-service-account-permissions)

  - [Pubsub Quotas](/runbook/steps/pubsub/pubsub-quotas)

  - [Response Code Step](/runbook/steps/pubsub/response-code-step)

  - [Active Subscription](/runbook/steps/pubsub/active-subscription)

  - [Throughput Qualification](/runbook/steps/pubsub/throughput-qualification)

  - [Dead Letter Topic](/runbook/steps/pubsub/dead-letter-topic)

  - [Dead Letter Topic Permissions](/runbook/steps/pubsub/dead-letter-topic-permissions)

  - [Gcs Subscription Delivery End](/runbook/steps/pubsub/gcs-subscription-delivery-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
