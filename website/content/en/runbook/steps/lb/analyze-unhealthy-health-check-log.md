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

Common reasons for UNHEALTHY detailed state:
* Health check is configured for a path to which application is not responding. In this case, the probes are responded with 404 response. Solution is to either change the health check path or configure the application to provide a successful response on the path configured on the health check.
* Backend server has received a HTTP request, which is not compliant with the application's expectations, from the health check probers. In this case, the probes are responded with 400 response. The failure message is 'Bad Request [Code: 400]'. Possible reason for the backend server to serve 400 response is:
    * A missing or wrong Host header received.
    * The health checker sends a request using a protocol version that the application doesn't support or expects in a different format. Examples:
        * Client sends HTTP/1.0 but server requires HTTP/1.1+ and interprets the request as invalid.
        * Client sends HTTP/2 frames to a plain HTTP/1.1 endpoint (without proper upgrade negotiation).
        * Client sends TLS-encrypted data to an HTTP (non-TLS) port — server tries to parse the Client Hello as an HTTP request, resulting in an improper request, and returns 400.
    * Unexpected query parameters in the request sent by the health check probers.
* TLS version mismatch between the health check probers and the backend server. The failure message will be Connect failed.
* Health check probes are responded with Service Unavailable, Service Temporarily Unavailable, Internal Server Error. In this case, the probes are responded with 5XX. Solution is to check:
    * if the backend instances are experiencing high CPU, memory, or network utilization, and as a result the customer backends are responding with 5XX.
    * if the instances are running a bad image. Bad instance images might have missing or improperly configured services, broken or ignored startup scripts, stale environment configurations.
    * CheckInterval config on the health check might be too short, leading to an excessive number of health checks sent to the backends, leading to high network utilization on the backends
* Some backends are configured to use a different port/protocol for health checks, than the named port assigned for traffic by the load balancer. In such a case, if the correct port is not configured in the backend, this can become problematic. In the health check logs, the failure explanation is visible as Connection refused, HTTP response: , Error: Connection refused or HTTP response: , Error: Connection reset by peer. Solution is to make the backend application listen on the port that is configured for the health check purposes or to change the health check port to the port on which the application is listening.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
