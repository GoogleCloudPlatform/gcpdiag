---
title: "pubsub/Dead Letter Topic Permissions"
linkTitle: "Dead Letter Topic Permissions"
weight: 3
type: docs
description: >
  "Verifies that the Pub/Sub service agent has the necessary IAM permissions   for the configured Dead Letter Topic.
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)\
**Step Type**: AUTOMATED STEP

### Description

This step checks if the pubsub agent has the relevant permissions to move
  messages whose processing has failed continuously to the dead letter topic.

### Failure Remediation

  Please ensure both the publisher role to the dead letter topic/project
  level and the subscriber role at the subscription/project level to the
  pubsub agent {} are assigned




<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
