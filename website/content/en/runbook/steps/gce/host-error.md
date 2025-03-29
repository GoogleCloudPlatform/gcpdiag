---
title: "gce/Host Error"
linkTitle: "Host Error"
weight: 3
type: docs
description: >
  Investigate the cause of a host error
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

Host errors should be rare. This step provides insights into the root cause of the issue.

### Failure Reason

{status_message}

### Failure Remediation

A host error (compute.instances.hostError) means that there was a hardware or software issue
on the physical machine hosting your VM that caused your VM to crash. A host error which
involves total hardware/software failure might prevent a live migration of your VM. If
your VM is set to automatically restart, which is the default setting, Google restarts your
VM, typically within three minutes from the time the error was detected. Depending on the
issue, the restart might take up to 5.5 minutes.

Note that this is a known behavior that cannot be completely eliminated and should be planned
for while designing your systems on GCE.

Mitigation Strategies
The following mitigation strategies are implemented by Google to prevent & minimize occurrence
of such events:

Live Migrations. Live migration lets Google Cloud perform maintenance without interrupting a
workload, rebooting a VM, or modifying any of the VM's properties, such as IP addresses,
metadata, block storage data, application state, and network settings. Additionally our
systems proactively monitor for hardware or software failure symptoms on hosts. If a potential
failure is detected, we initiate live migration to seamlessly relocate the VM and prevent
termination. A 'hostError' will only occur in the rare instance where the failures prevent
successful live migration.

Google reliability engineering. We are continuously monitoring the health of GCP hosts and
taking steps to prevent errors from occurring, while using a variety of HA techniques to
detect and mitigate hardware failures, such as using redundant components and monitoring for
signs of failure.

Software Patching: We are continuously implementing a rigorous software patching schedule to
ensure the timely application of security updates and bug fixes. This proactive approach is
mitigating the risk of software defects, and bugs that could lead to operational instability.

RCA
Kindly note:
RCA by Google for Host errors is not common practice. Host errors can happen occasionally and
typically do not undergo individual RCA. Should you request an RCA for a host error, you must
provide a compelling business justification for why further details are necessary.

Any root cause provided will be limited to if the issue was hardware or software related and
if it was related to a single host or a rack.

Review Logs and Create Log-Based Metrics:
For tracking HostErrors: To proactively track host errors within your projects, create a
log-based metric dashboard. This will provide a visual representation of error trends.
For customer-facing evidence: If you need root cause information as evidence for your own
customers, utilize Cloud Logging to query and export relevant logs. These logs provide
granular error messages and timestamps.

For timely response to errors: To ensure prompt reaction to critical host errors,
configure a log-based alert.

Alerting (2)

Follow the Instructions here using the below query to build a log based alert on your project
to get notified in case of a hostError.

Make sure to include labels with the information you need exposed on the notification.

resource.type="gce_instance"
protoPayload.serviceName="compute.googleapis.com"
(protoPayload.methodName:"compute.instances.hostError" OR
operation.producer:"compute.instances.hostError")
log_id("cloudaudit.googleapis.com/system_event")

Resources:
[1]
<https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-reboots#:~:text=Getting%20support.-,Method,compute.instances.hostError,-System%20event>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
