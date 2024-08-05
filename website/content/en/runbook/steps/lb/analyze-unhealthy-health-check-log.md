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

In the health check logs, we found logs with the detailed health state UNHEALTHY, which means the endpoint is reachable but does not conform to the requirements defined by the health check.
The following responses were received from your backends: {probe_results_text_str}

### Uncertain Remediation

{success_criteria}

Please investigate the configuration of your application to ensure it aligns with these health check expectations.

If you intend to check a different endpoint or expect a different response, adjust the health check settings accordingly.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
