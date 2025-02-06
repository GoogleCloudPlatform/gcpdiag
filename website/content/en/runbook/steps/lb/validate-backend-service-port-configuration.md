---
title: "lb/Validate Backend Service Port Configuration"
linkTitle: "Validate Backend Service Port Configuration"
weight: 3
type: docs
description: >
  Checks if health check sends probe requests to the different port than serving port.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Success Reason

The load balancer is performing health checks on the same port that it is using for serving traffic. This is the standard configuration.

### Uncertain Reason

The load balancer is conducting health checks on port {hc_port} for the backend service {bs_resource}. However, this health check port differs from the port used by the load balancer for serving traffic on some backend instance groups. The backend service is configured to use the "{serving_port_name}" port, which is then translated to a specific port number based on the "{serving_port_name}" port mapping within each backend instance group.

Affected backends:
{formatted_igs}

This configuration can be problematic unless you have configured the load balancer to use a different port for health checks purposefully.

### Uncertain Remediation

Verify that the health check port is correctly configured to match the port used by your application if the health check is intended to check the serving port.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
