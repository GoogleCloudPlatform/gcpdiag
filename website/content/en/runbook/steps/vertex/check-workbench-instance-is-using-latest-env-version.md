---
title: "vertex/Check Workbench Instance Is Using Latest Env Version"
linkTitle: "Check Workbench Instance Is Using Latest Env Version"
weight: 3
type: docs
description: >
  Check if the Workbench Instance is using the latest environment version
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: AUTOMATED STEP

### Description

Workbench Instances can be upgraded regularly to have the latest fixes

### Failure Reason

Workbench Instance {instance_name} is using a previous environment version M{environment_version}

### Failure Remediation

Upgrade the instance to use the latest version {upgrade_version} which has the latest updates and fixes [1]
Upgrade version image: {upgrade_image}
Remember to backup your data before an upgrade.
[1] <https://cloud.google.com/vertex-ai/docs/workbench/instances/upgrade>

### Success Reason

OK! Workbench Instance {instance_name} is using the latest environment version M{environment_version}

### Uncertain Reason

Workbench Instance {instance_name} should be in STOPPED state to check its upgradability.
Upgradability info: {upgrade_info}

### Uncertain Remediation

Stop the instance.


### Uncertain Reason [Alternative 2]

Workbench Instance {instance_name} upgradability info:
{upgrade_info}

### Uncertain Remediation [Alternative 2]

Make sure instance has the latest environment version.


<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
