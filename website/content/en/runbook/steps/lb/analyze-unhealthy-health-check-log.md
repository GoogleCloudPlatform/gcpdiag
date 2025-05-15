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

### Failure Reason

Health check logs for backend service {bs_url} indicate a detailed health state of UNHEALTHY. The backend instances are reachable but are not passing the health check requirements.

Responses received from backends: {probe_results_text_str}

### Failure Remediation

{success_criteria}

Investigate the configuration of the application to ensure it aligns with these health check expectations.

If a different endpoint should be checked or a different response is expected, adjust the health check settings accordingly.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
