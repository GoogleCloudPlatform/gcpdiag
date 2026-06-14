---
title: "pubsub/Response Code Step"
linkTitle: "Response Code Step"
weight: 3
type: docs
description: >
  Check push request responses from the endpoint.
---

**Product**: [Cloud Pub/Sub](https://cloud.google.com/pubsub/)\
**Step Type**: AUTOMATED STEP

### Description

This step checks the responses coming from the endpoint and the
  success rates.

### Failure Reason

  Non-OK responses from the endpoint detected [1].

  [1] <https://cloud.google.com/pubsub/docs/push#receive_push>

### Failure Remediation

  Resolve the endpoint errors processing messages to enable successful delivery.

  Common errors codes:
  - 431: payload exceeds allowed header limits. Disable write metadata [1]
  - 401/403: if enabled, ensure the push subscription authentication abides by the requirements. [2] Otherwise check permission errors at the endpoint.
  - 400: investigate the correctness of the message attributes & the http endpoint.

  [1] <https://cloud.google.com/pubsub/docs/payload-unwrapping#how_payload_unwrapping_works>.
  [2] <https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions#configure_for_push_authentication>.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
