---
title: "interconnect/Bgp Down Flap Start"
linkTitle: "Bgp Down Flap Start"
weight: 3
type: docs
description: >
  Check if the project and other parameters are valid and vlan attachments are available.
---

**Product**: [Interconnect](https://cloud.google.com/network-connectivity/docs/interconnect)\
**Step Type**: START

### Description

This step starts the BGP issue debugging process by
  verifying the correct input parameters have been provided and checking to ensure
  that the following resources exist.
    - The Project
    - Region
    - The vlan attachments exist for the given project

### Success Reason

    Vlan attachments are found in the project.

### Skipped Reason

    Unable to fetch the vlan attachents in {project_id}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
