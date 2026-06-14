---
title: "pubsub/Active Subscription"
linkTitle: "Active Subscription"
weight: 3
type: docs
description: >
  Has common step to validate if the subscription is active.
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)\
**Step Type**: AUTOMATED STEP

### Description

This step checks if the subscription is in active (valid) state.

### Failure Remediation

  Increase subscription throughput to keep it active, or amend the persistence configuration. [1].

  [1] <https://cloud.google.com/pubsub/docs/subscription-overview#lifecycle>.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
