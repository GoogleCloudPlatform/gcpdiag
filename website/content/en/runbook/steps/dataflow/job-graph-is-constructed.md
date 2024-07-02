---
title: "dataflow/Job Graph Is Constructed"
linkTitle: "Job Graph Is Constructed"
weight: 3
type: docs
description: >
  Has common step to check if the job has an error in graph construction.
---

**Product**: [Dataflow](https://cloud.google.com/dataflow)\
**Step Type**: GATEWAY

### Description

If a job fails during graph construction, it's error is not logged in the
  Dataflow Monitoring Interface as it never launched. The error appears in the
  console or terminal window where job is ran and may be language-specific.
  Manual check if there's any error using the 3 supported languages: Java,
  Python, Go.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
