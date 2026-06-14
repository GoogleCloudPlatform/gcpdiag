---
title: "pubsub/Vpc Sc Step"
linkTitle: "Vpc Sc Step"
weight: 3
type: docs
description: >
  Check if the VPC-SC api is enabled
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)\
**Step Type**: AUTOMATED STEP

### Description

This step highlights caveats of using VPC-SC with push subscriptions

### Failure Remediation

  Beware of limitations when using push subscriptions with VPCSC [1] such as:
  - You can't update existing push subscriptions, they continue to function but aren't protected by VPC Service Controls
  - Custom domains don't work, you can only create new push subscriptions for which the push endpoint is set to a Cloud Run service
  - You can only create new push subscriptions through Eventarc for Eventarc workflows
  - Use the fully qualified name of the topic if terraform/deployment manager is used to attach dead letter topics

  [1] <https://cloud.google.com/pubsub/docs/create-push-subscription#vpc-service-control>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
