---
title: "lb/Analyze Unknown Health Check Log"
linkTitle: "Analyze Unknown Health Check Log"
weight: 3
type: docs
description: >
  Analyze logs with detailed health state UNKNOWN.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Uncertain Reason

Health check logs for backend service {bs_url} show entries with the detailed health state UNKNOWN. This indicates that the health checking system is aware of the instance, but its health status is undetermined. This situation can arise when a new endpoint is unresponsive to health checks and there's a substantial configured timeout period (approximately 25 seconds or longer). In such cases, the "UNKNOWN" state might be published while the health checker waits for the timeout to expire. Additionally, "UNKNOWN" could also be published during outage scenarios if the health checkers themselves are crashing. In this critical situation, endpoints that previously had known health states could transition to "UNKNOWN".

### Uncertain Remediation

For new endpoints: Consider reducing the timeout period for health checks if appropriate, especially during initial setup or testing phases.

For potential Google Cloud outages: Use Personalized Service Health to check for any ongoing incidents that might be affecting your project or the specific service in question. If an incident is identified, follow any recommended mitigation steps or wait for the issue to be resolved by Google Cloud.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
