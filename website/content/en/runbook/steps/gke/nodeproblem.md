---
title: "gke/Nodeproblem"
linkTitle: "Nodeproblem"
weight: 3
type: docs
description: >
  This will confirm if there is any VPC flow logs to destination IP.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

This will either rule out ip-masq issue or points to ip-mas-agent issue.

### Failure Reason

There are no egress traffic to Destination IP which indicates that GKE NODE is also having issue to connect to destination IP.
{LOG_ENTRY}

### Failure Remediation

Enable VPC flow logs by following the documentation and look if traffic id going out to destination:
https://cloud.google.com/vpc/docs/using-flow-logs#enable-logging-existing

### Success Reason

When VPC flow logs shows traffic is going out, then GKE IP masquerading may be working as intended. If the end-to-end case is still failing, the problem is likely to be somewhere in the networking path between Dest-IP and node on which impacted Pod is scheduled.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
