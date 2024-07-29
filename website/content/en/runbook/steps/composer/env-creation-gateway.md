---
title: "composer/Env Creation Gateway"
linkTitle: "Env Creation Gateway"
weight: 3
type: docs
description: >
  Selects a Composer environment and service account for troubleshooting.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This gateway interacts with the user to identify the specific Composer
  environment and associated service account that requires troubleshooting.

  The process consists of the following steps:

  1. **Environment Selection:**
     - Displays a numbered list of available Composer environments in the
     project.
     - Prompts the user to choose an environment by entering its corresponding
     number.
     - Validates the input to ensure it's within the valid range.

  2. **Service Account Selection:**
     - Asks if the user wants to use the default service account of the chosen
     environment.
     - If yes, it uses the environment's default service account.
     - If no, it prompts the user to enter a service account email address.
     - Validates the entered email address to ensure its format is correct.

  3. **Storage of Results:**
     - Stores the selected environment in the `op` context under the key
     `selected_composer_env`.
     - Stores the chosen service account in the `op` context under the key
     `selected_service_account`.

  **Key Features:**

  - User-friendly interaction for environment and service account selection.
  - Robust input validation to prevent errors due to invalid choices.
  - Clear storage of selected information in the `op` context for further use in
  the runbook.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
