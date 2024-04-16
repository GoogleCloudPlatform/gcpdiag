---
title: "gcp/Service Api Status Check"
linkTitle: "Service Api Status Check"
weight: 3
type: docs
description: >
  Check whether or not a service has been enabled for use by a consumer
---

**Product**: \
**Step Type**: AUTOMATED STEP

### Description

Checks is a Cloud API service is enabled or not. Guides the user to enable
  the service if it's expected to be enabled and vice versa.

  Attributes:
      api_name (str): The name of the service to check.
      expected_state (str): The expected state of the service, used to verify
                            against the actual service state retrieved during
                            execution. API state has to be one of the value of
                            gcp.constants.APIState

### Failure Reason

The `{service_name}` service is not in the exptected state `{expected_state}`

### Failure Remediation

This service is expected to be enabled.
Execute the command below to enable {service_name} in {project_id}

gcloud services enable {service_name} --project={project_id}

Resources
https://cloud.google.com/service-usage/docs/enable-disable#enabling

### Success Reason

The `{service_name}` service is currently in the expected state: `{expected_state}`.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
