---
title: "lb/Validate Backend Service Port Configuration"
linkTitle: "Validate Backend Service Port Configuration"
weight: 3
type: docs
description: >
  Checks if health check sends probe requests to the different port than serving port.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Success Reason

The load balancer is performing health checks on the same port used for serving traffic. This is the standard configuration.

### Uncertain Reason

The load balancer is conducting health checks on port {hc_port} for the backend service {bs_resource}. However, this health check port differs from the port used by the load balancer for serving traffic on some backend instance groups. The backend service is configured to use the "{serving_port_name}" port, which is then translated to a specific port number based on the "{serving_port_name}" port mapping within each backend instance group.

Affected backends:

{formatted_igs}

This configuration can be problematic unless the load balancer has been configured to use a different port for health checks purposefully.

### Uncertain Remediation

1.  **Verify Intent:** Confirm if the health check port `{hc_port}` is *meant* to be different from the serving port defined by "{serving_port_name}" on the backends.

2.  **Test Port on Backend VMs:** Check if port `{hc_port}` is listening on an instance from the affected groups. Run this command from your local machine/Cloud Shell:

    ```bash
    gcloud compute ssh [INSTANCE_NAME] --zone [ZONE] --project {project_id} --command="sudo ss -tlnp | grep ':{hc_port}'"
    ```
    *   Output showing `LISTEN` indicates the port is open and your application is likely listening.
    *   No output suggests the port is not in a listening state on that VM.

3.  **Adjust Configuration:**
    *   **If Mismatch is Unintentional:** Align the load balancer's health check port in the backend service `{bs_resource}` to match the actual port number used by "{serving_port_name}" in the instance groups.
    *   **If Mismatch is Intentional:** Ensure your application on the VMs is correctly configured to listen on port `{hc_port}`.
    *   **If Port Not Listening:** Troubleshoot your application on the VM to ensure it's running and bound to port `{hc_port}`. Check the VM's local firewall as well.

If the health check port `{hc_port}` is meant to be different from the serving port (e.g., a dedicated management/health endpoint), confirm that your application is correctly configured to listen on the health check port.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
