---
title: "{{cookiecutter.product}}/{{cookiecutter.severity}}/{{cookiecutter.year}}_{{cookiecutter.number}}"
linkTitle: "{{cookiecutter.severity}}/{{cookiecutter.year}}_{{cookiecutter.number}}"
weight: 1
type: docs
description: >
  {{cookiecutter.title}}
---

**Product**: {{ cookiecutter.__products[cookiecutter.product] | default("") }}\
**Rule class**: {{ cookiecutter.__rule_classes[cookiecutter.severity] | default("") }}

### Description

{{cookiecutter.description}}

Add a more detailed description here. Preferably, refer to an existing public page that provides detailed information and briefly explain the issue here.

Remember, gcpdiag findings **must** be actionable. If there's no way to remediate/fix the issue, the linter rule shouldn't be created in the first place.

Use [`Code Blocks`](https://www.markdownguide.org/extended-syntax/#fenced-code-blocks) MD formatting for logging/monitoring queries and `gcloud` commands. For logging queries, be as specific as possible and follow the [Logging Query best practices](https://cloud.google.com/logging/docs/view/logging-query-language#finding-quickly).


Sample logging query:
```
resource.type="k8s_cluster"
severity="WARNING"
jsonPayload.message:"Please enable the gateway API for your cluster using gcloud"
```

Sample gcloud command:
```
gcloud compute disks list --filter="-users:*"
```

You can use tables if needed. Sample table:

| \#  | DeamonSet name | GKE Feature       |
| --- | -------------- | ----------------- |
| 1   | kube-proxy     | non-DPv2 clusters |
| 2   | fluentbit-gke  | GKE Logging       |

### Remediation

Explain how to remediate the issue. Make sure the steps are clear and very specific. Prefer `gcloud` commands over a set of steps for the Cloud Console (Web UI). The user should be able to mitigate the issue independently by following the steps provided here.

Preferably, refer to existing public web pages with troubleshooting steps instead of copying that information here.

**Sample troubleshooting public page:** https://cloud.google.com/kubernetes-engine/docs/troubleshooting#CrashLoopBackOff


### Further information

- [Link title 1](https://cloud.google.com/link-1)
- [Link title 2](https://cloud.google.com/link-2)
