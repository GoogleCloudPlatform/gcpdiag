---
title: "pubsub/Dead Letter Topic"
linkTitle: "Dead Letter Topic"
weight: 3
type: docs
description: >
  Has common step to check if the subscription has a dead letter topic.
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)\
**Step Type**: AUTOMATED STEP

### Description

This step checks if the subscription has a Dead Letter Topic attached.
  This is important to remove the messages that have failed processing out of the
  main subscription.

### Failure Reason

  No dead letter topic attached. [1]

  [1] <https://cloud.google.com/pubsub/docs/handling-failures#dead_letter_topic>

### Failure Remediation

  Add dead letter topic to deliver to the topic any messages whose delivery retries has exceeded the threshold.
  Be aware that this is on best effort [1] and ensure the proper permissions are assigned [2].
  Monitor dead-lettered message count[3] and pull from the subscription attached to the dead letter topic to investigate the message processing failures [4].

  [1] <https://cloud.google.com/pubsub/docs/handling-failures#how_dead_letter_topics_work>
  [2] <https://cloud.google.com/pubsub/docs/handling-failures#grant_forwarding_permissions>
  [3] <https://cloud.google.com/pubsub/docs/handling-failures#monitor_forwarded_messages>
  [4] <https://cloud.google.com/pubsub/docs/handling-failures#track-delivery-attempts>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
