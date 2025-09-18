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

The load balancer is performing health checks using the same protocol ({hc_protocol}) used for serving traffic on backend service {bs_resource}. This is the standard configuration.

### Uncertain Reason

The load balancer uses {serving_protocol} for traffic but {hc_protocol} for health checks on backend service {bs_resource}. If not intended, this protocol mismatch can lead to incorrect health assessments, potentially causing traffic to be sent to failing backends or triggering unnecessary failovers.

Here are some examples of potentially problematic mismatches:

*   **TLS vs. Non-TLS:**
    *   Health Check: HTTPS, Backend: HTTP - The health check will try to initiate a TLS handshake, which will fail against a non-TLS server.
    *   Health Check: HTTP, Backend: HTTPS - The health check sends plaintext, but the server expects TLS, likely resulting in a connection reset or protocol error.

*   **Application Protocol Mismatch:**
    *   Health Check: GRPC, Backend: HTTP - The health check speaks the GRPC protocol, but the backend expects standard HTTP requests.
    *   Health Check: HTTP, Backend: SSL - The health check expects an HTTP application response, but the backend is configured for generic SSL, which might not involve HTTP.

*   **Protocol Version/Feature Mismatch (Subtler issues even with the same base protocol):**
    *   An HTTP/1.0 health check request to a server strictly requiring HTTP/1.1 features.
    *   An HTTP/2 health check to a server only supporting HTTP/1.1 without proper negotiation.

**Important:** Health checks using {hc_protocol} might be passing while the application serving {serving_protocol} traffic is failing because the success criteria for the two protocols can differ. More details on the health check success criteria can be found in [docs](https://cloud.google.com/load-balancing/docs/health-check-concepts#criteria-protocol-http).

### Uncertain Remediation

1.  Verify if this protocol difference is intentional and well-understood.
2.  If not, **align the health check protocol with the serving protocol ({serving_protocol})** to ensure health checks accurately represent the backend's ability to serve traffic.
3.  Consult the [Health Checks Overview](https://cloud.google.com/load-balancing/docs/health-check-concepts) for best practices.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
