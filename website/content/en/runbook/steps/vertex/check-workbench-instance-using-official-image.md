---
title: "vertex/Check Workbench Instance Using Official Image"
linkTitle: "Check Workbench Instance Using Official Image"
weight: 3
type: docs
description: >
  Check if the Workbench Instance is using the official images
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: AUTOMATED STEP

### Description

Users have the option to create Workbench Instances with any image
  However, only 'workbench-instances' official images are supported

### Failure Reason

image: {image}
images without '{images_family}' text in the image name are not supported but might work with Workbench Instances [1]
[1] <https://cloud.google.com/vertex-ai/docs/workbench/instances/introduction#limitations>

### Failure Remediation

Users are responsible for customizing unsupported images or custom containers
Create a Workbench Instance with the official '{images_family}' family of images.
Officially supported images are found in the Google Cloud Console:
Vertex AI Workbench UI > Instances > Create form > Advanced > Environment > Previous versions dropdown.
You may also follow the documentation [1] to use Custom Containers
[1] <https://cloud.google.com/vertex-ai/docs/workbench/instances/create-custom-container>

### Success Reason

OK! Workbench Instance {instance_name} is using an official '{image_family}' image: {image}

### Uncertain Reason

image: {image}
'{images_family}' images might work with Workbench Instances, but are unsupported [1]
[1] <https://cloud.google.com/vertex-ai/docs/workbench/instances/introduction#limitations>

### Uncertain Remediation

Officially supported images are found in the Google Cloud Console:
Vertex AI Workbench UI > Instances > Create form > Advanced > Environment > Previous versions dropdown.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
