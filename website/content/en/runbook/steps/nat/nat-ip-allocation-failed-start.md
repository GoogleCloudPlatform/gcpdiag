---
title: "nat/Nat Ip Allocation Failed Start"
linkTitle: "Nat Ip Allocation Failed Start"
weight: 3
type: docs
description: >
  Start Nat IP Allocation Failed Checks.
---

**Product**: [Cloud NAT](https://cloud.google.com/nat)\
**Step Type**: START

### Description

This step steps starts the NAT IP Allocation Failed Check debugging process by
  verifying the correct input parameters have been provided and checking to ensure
  that the following resources exist.
    - The Project
    - VPC Network
    - The NAT Cloud Router

### Skipped Reason

Unable to fetch the network {netwrok} confirm it exists in the project {project_id}.


### Skipped Reason [Alternative 2]

Cannot find the NAT cloud router: {cloud_router} in the region {region} for the project {project_id}

Check the cloud router name to ensure it exists in the project and rerun.


### Skipped Reason [Alternative 3]

Cannot find the NAT Gateway: {nat_gateway} in the region {region} for the project {project_id}

Check the cloud router name to ensure it exists in the project and rerun.

<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
