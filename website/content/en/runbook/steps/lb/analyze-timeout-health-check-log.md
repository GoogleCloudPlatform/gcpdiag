---
title: "lb/Analyze Timeout Health Check Log"
linkTitle: "Analyze Timeout Health Check Log"
weight: 3
type: docs
description: >
  Analyzes logs with the detailed health check state TIMEOUT
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Uncertain Reason

Health check logs for backend service {bs_url} show the detailed health state "TIMEOUT".

Responses received from backends: {probe_results_text_str}

The backend might be timing out because:

1. The application is overloaded and taking too long to respond.

2. The backend service or health check timeout is too low.

3. Connection to the endpoint cannot be established - the backend instance has crashed or is otherwise unresponsive.

The following responses were received from your backends: {probe_results_text_str}

### Uncertain Remediation

1. Make sure that the backend service timeout (current value: {bs_timeout_sec}s) and health check timeout (current value: {hc_timeout_sec}s) are appropriately configured to accommodate your application's expected response time.

2. Investigate your application's configuration to ensure it is correctly handling health check probe requests. {success_criteria}

3. Check if firewall rules or iptables configurations are blocking the health check probes from reaching the backend instances, resulting in timeouts.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
