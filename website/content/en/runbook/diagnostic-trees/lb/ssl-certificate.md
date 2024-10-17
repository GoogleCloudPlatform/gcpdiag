---
title: "lb/Ssl Certificate"
linkTitle: "lb/ssl-certificate"
weight: 3
type: docs
description: >
  This runbook diagnoses and troubleshoots issues with SSL certificates.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)
**Kind**: Debugging Tree

### Description

The supported certificates are Google-managed classic certificates attached to
  load balancers.

  It helps identify and resolve common problems that prevent certificates from
  provisioning or functioning correctly.

  Key Investigation Area:

  - Certificate Status:
    - Checks the certificate's provisioning status and identifies any failed
    domains.
  - Domain Validation:
    - Verifies DNS configuration for each domain, ensuring proper A/AAAA records
    and the absence of conflicting records.
  - Load Balancer Configuration:
    - Confirms the certificate is correctly attached to a target proxy and
    associated with a forwarding rule using port 443.
  - Conflicting resources:
    - Ensures no certificate map is attached to the target proxy, which can
    interfere with Google-managed certificates.
  - Provisioning Time:
    - Checks Cloud Logging to determine when the certificate was attached and
    allows sufficient time for propagation.

### Executing this runbook

```shell
gcpdiag runbook lb/ssl-certificate \
  -p project_id=value \
  -p certificate_name=value \
  -p region=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `certificate_name` | True | None | str | The name of the SSLcertificate that you want to investigate |
| `region` | False | global | str | The region of the SSL certificate. If not provided, the SSL cer is assumed to be global. |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Ssl Certificate Start](/runbook/steps/lb/ssl-certificate-start)

  - [Analyze Certificate Status](/runbook/steps/lb/analyze-certificate-status)

  - [Analyze Domain Statuses](/runbook/steps/lb/analyze-domain-statuses)

  - [Analyze Failed Not Visible Domains](/runbook/steps/lb/analyze-failed-not-visible-domains)

  - [Analyze Failed Not Visible Domains](/runbook/steps/lb/analyze-failed-not-visible-domains)

  - [Analyze Failed Not Visible Domains](/runbook/steps/lb/analyze-failed-not-visible-domains)

  - [Analyze Failed Not Visible Domains](/runbook/steps/lb/analyze-failed-not-visible-domains)

  - [Check Certificate Attachment](/runbook/steps/lb/check-certificate-attachment)

  - [Ssl Certificate End](/runbook/steps/lb/ssl-certificate-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
