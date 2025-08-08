---
title: "lb/Verify Dns Records"
linkTitle: "Verify Dns Records"
weight: 3
type: docs
description: >
  Check the DNS records for specific domain associated with the SSL certificate.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: GATEWAY

### Description

None

### Failure Reason

DNS records for domain {domain} currently resolve to the following IP addresses: {unresolved_ip_addresses}. These IP addresses do not point to any load balancer associated with certificate {name}. Certificate provisioning is therefore blocked.

### Failure Remediation

Configure DNS records for {domain} to point to the correct load balancer IP address(es) for certificate {name}.

The following load balancer IP addresses are associated with this certificate:

{fr_ip_message}

Check: <https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs#update-dns>

### Success Reason

DNS records for domain {domain} are correctly configured. All resolved IP addresses ({ip_addresses}) point to the load balancer(s) associated with certificate {name}.

### Uncertain Reason

Some DNS records for domain {domain} resolve to the following unexpected IP address(es): {unresolved_ip_addresses}.  While other records point to the expected IP addresses: {resolved_ip_addresses}. The unexpected IP addresses do not point to any load balancer associated with certificate {name}. This can cause certificate provisioning issues.

### Uncertain Remediation

Configure DNS records for {domain} to point to the correct load balancer IP address(es) for certificate {name}.

The following load balancer IP addresses are associated with this certificate:

{fr_ip_message}

Check: <https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs#update-dns>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
