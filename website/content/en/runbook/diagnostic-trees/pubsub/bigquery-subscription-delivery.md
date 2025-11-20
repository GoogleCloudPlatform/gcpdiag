---
title: "pubsub/Bigquery Subscription Delivery"
linkTitle: "pubsub/bigquery-subscription-delivery"
weight: 3
type: docs
description: >
  Troubleshoot BigQuery Subscription Errors
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)
**Kind**: Debugging Tree

### Description

A diagnostic guide to help you resolve common issues
causing message delivery failures from Pub/Sub to BigQuery.

### Executing this runbook

```shell
gcpdiag runbook pubsub/bigquery-subscription-delivery \
  -p project_id=value \
  -p subscription_name=value \
  -p table_id=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `subscription_name` | True | None | str | The Pub/Sub subscription ID |
| `table_id` | True | None | str | The BigQuery table ID in the format "project_id:dataset.table" or "dataset.table" |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Start Step](/runbook/steps/gcpdiag/start-step)

  - [Subscription Existence Check](/runbook/steps/pubsub/subscription-existence-check)

  - [Big Query Table Existence Check](/runbook/steps/pubsub/big-query-table-existence-check)

  - [Big Query Writer Permission Check](/runbook/steps/pubsub/big-query-writer-permission-check)

  - [Subscription Status Check](/runbook/steps/pubsub/subscription-status-check)

  - [Pubsub Quotas](/runbook/steps/pubsub/pubsub-quotas)

  - [Investigate Bq Push Errors](/runbook/steps/pubsub/investigate-bq-push-errors)

  - [Throughput Qualification](/runbook/steps/pubsub/throughput-qualification)

  - [Dead Letter Topic](/runbook/steps/pubsub/dead-letter-topic)

  - [Dead Letter Topic Permissions](/runbook/steps/pubsub/dead-letter-topic-permissions)

  - [End Step](/runbook/steps/gcpdiag/end-step)


<!--
This file is auto-generated. DO NOT EDIT.
-->
