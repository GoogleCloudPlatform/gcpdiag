---
title: "dataproc/Check Bq Connector"
linkTitle: "Check Bq Connector"
weight: 3
type: docs
description: >
  Check for issues related to BigQuery connector such as version dependency conflicts.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: COMPOSITE STEP

### Description

None

### Success Reason

The cluster uses image version {image_version} which preinstalls the BigQuery connector, and no conflicting BigQuery JARs were provided. Dependency version conflicts on the BigQuery side are not expected.

Refer to the Dataproc Version page to find out each component version preinstalled on your cluster:
<https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters>

### Uncertain Reason

The cluster uses image version {image_version} which preinstalls the BigQuery connector, and a different version of the BigQuery connector is being installed at the cluster or job level. This might cause dependency version conflicts and lead to job failures.

### Uncertain Remediation

Resolve potential BigQuery connector version conflicts using one of the following approaches:

- If providing the BigQuery JAR at the cluster level: Create the Dataproc cluster without specifying any BigQuery JAR.
- If providing the BigQuery JAR at the job level: Run the job without specifying any BigQuery JAR.
- If installing a BigQuery JAR is necessary: Match the version of the BigQuery JAR to the version preinstalled on the cluster (version {bq_version} for image {image_version}).

Refer to the Dataproc Version page to find out each component version preinstalled on your cluster:
<https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
