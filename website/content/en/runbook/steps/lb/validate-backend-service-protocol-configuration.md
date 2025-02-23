---
title: "lb/Validate Backend Service Protocol Configuration"
linkTitle: "Validate Backend Service Protocol Configuration"
weight: 3
type: docs
description: >
  Checks if health check uses the same protocol as backend service for serving traffic.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Success Reason

The load balancer is performing health checks using the same protocol ({hc_protocol}) that it is using for serving traffic. This is the standard configuration.

### Uncertain Reason

The load balancer uses {serving_protocol} for traffic but {hc_protocol} for health checks on backend service {bs_resource}. If not intended, this protocol mismatch can lead to incorrect health assessments, potentially causing traffic to be sent to failing backends or triggering unnecessary failovers.

**Important:** Health checks using {hc_protocol} might be passing while the application serving {serving_protocol} traffic is failing because the success criteria for the two protocols can differ. More details on the health check success criteria can be found in [docs](https://cloud.google.com/load-balancing/docs/health-check-concepts#criteria-protocol-http).

### Uncertain Remediation

Verify that the health check and serving protocol are correctly configured to match the protocol used by your application.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
