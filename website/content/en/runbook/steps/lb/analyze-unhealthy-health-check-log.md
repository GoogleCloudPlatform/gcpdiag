---
title: "lb/Analyze Unhealthy Health Check Log"
linkTitle: "Analyze Unhealthy Health Check Log"
weight: 3
type: docs
description: >
  Analyzes logs with detailed health state UNHEALTHY.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Uncertain Reason

Health check logs show the detailed health state UNHEALTHY meaning the endpoint is reachable but doesn't meet the health check requirements.
Responses received from backends: {probe_results_text_str}

### Uncertain Remediation

{success_criteria}

Please investigate the configuration of your application to ensure it aligns with these health check expectations.

If you intend to check a different endpoint or expect a different response, adjust the health check settings accordingly.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
