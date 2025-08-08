---
title: "lb/Verify Firewall Rules"
linkTitle: "Verify Firewall Rules"
weight: 3
type: docs
description: >
  Checks if firewall rules are configured correctly.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

{insight}
The health checks are currently failing due to a misconfigured firewall. This prevents Google Cloud probers from connecting to the backends, causing the load balancer to consider them unhealthy.

### Failure Remediation

Update the firewall rules to allow inbound traffic from the Google Cloud health check IP ranges (found at <https://cloud.google.com/load-balancing/docs/health-check-concepts#ip-ranges>) to the backends.

### Success Reason

Firewall rules are correctly configured and are not blocking health check probes for backend service {bs_url}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
