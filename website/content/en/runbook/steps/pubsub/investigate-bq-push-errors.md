---
title: "pubsub/Investigate Bq Push Errors"
linkTitle: "Investigate Bq Push Errors"
weight: 3
type: docs
description: >
  Investigate message backlog issues for BigQuery subscriptions using push metrics.
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

  Message failures detected.

  [1] <https://docs.cloud.google.com/pubsub/docs/reference/error-codes>

### Failure Remediation

  Handle message failures

  When a Pub/Sub message cannot be written to BigQuery, the message cannot be acknowledged.
  The Pub/Sub message forwarded to the dead-letter topic contains an attribute CloudPubSubDeadLetterSourceDeliveryErrorMessage that has the reason that the Pub/Sub message couldn't be written to BigQuery.

  [1] <https://docs.cloud.google.com/pubsub/docs/bigquery#handle_message_failures>.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
