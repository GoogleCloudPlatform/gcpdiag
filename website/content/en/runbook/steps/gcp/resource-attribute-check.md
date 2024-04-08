---
title: "gcp/Resource Attribute Check"
linkTitle: "Resource Attribute Check"
weight: 3
type: docs
description: >
  Generalized step used to verify the value of a GCP resource's attribute.
---

**Product**: \
**Step Type**: AUTOMATED STEP

### Description

This step enables the flexible verification of attributes within any JSON-viewable GCP
    resource, such as GCE instances or Cloud Storage buckets. It checks if a specific resource's
    attribute matches an expected value and optionally supports custom evaluation logic for
    more complex verification scenarios.

    Attributes:
      resource_query (Callable): Function to fetch the target GCP resource. Must return
          a `Resource` object. Typically, this is one of the `gcpdiag.queries.*` methods.
      query_kwargs (dict): Keyword arguments to pass to `resource_query`.
      resource (Resource): The GCP resource fetched by `resource_query`.
      attribute (Optional[tuple]): Path to the nested attribute within the resource to be
          verified, represented as a tuple of strings. Utilizes `boltons.iterutils.get_path`
          for navigation.
      evaluator (Optional[Callable]): A custom function for performing complex evaluations
          on a resource attribute.
          Should return a dict:
            {'success_reason': {'key1': 'value1', ...}, 'failure_reason': {...}}
      expected_value (str): The expected value of the target attribute.
      expected_value_type (type): Data type of the expected attribute value. Defaults to `str`.
      extract_args (dict): Configuration for extracting additional information for message
          formatting, with keys specifying the argument name and values specifying the source
          and attribute path.
      message_args (dict): Extracted arguments used for formatting outcome messages.

    Usage:
      An example to check the status of a GCE instance:

      ```python
      status_check = ResourceAttributeCheck()
      status_check.resource_query = gce.get_instance
      status_check.query_kwargs = {
          'project_id': op.get(flags.PROJECT_ID),
          'zone': op.get(flags.ZONE),
          'instance_name': op.get(flags.NAME)
      }
      status_check.attribute = ('status',)
      status_check.expected_value = 'RUNNING'
      status_check.extract_args = {
          'vm_name': {'source': models.Resource, 'attribute': 'name'},
          'status': {'source': models.Resource, 'attribute': 'status'},
          'resource_project_id': {'source': models.Parameter, 'attribute': 'project_id'}
      }
      ```

    `get_path`: https://boltons.readthedocs.io/en/latest/_modules/boltons/iterutils.html#get_path

### Failure Reason

Resource doesn't have the expected value

### Failure Remediation

Update the resource to have the expected value

### Success Reason

Resrouce has the expected value



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
