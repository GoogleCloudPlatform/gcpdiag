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

The load balancer is performing health checks on port {hc_port}. We detected that within some backend instance groups, this is different than the port that the load balancer is using for serving traffic. The backend service is configured to use the "{serving_port_name}" port, which is translated to a port number based on the "{serving_port_name}" port mapping within each backend instance group.

Affected backends:
{formatted_igs}

This configuration can be problematic unless you have configured the load balancer to use a different port for health checks purposefully.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
