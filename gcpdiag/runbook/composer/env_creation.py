"""Composer Environment Creation Runbook."""

import logging
import re

from gcpdiag import runbook
from gcpdiag.queries import composer, crm, iam, kms, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import flags

PRODUCT_FLAG = 'composer'


class EnvCreation(runbook.DiagnosticTree):
  """Composer Runbook: Check for environment creation permissions."""

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True,
      },
      PRODUCT_FLAG: {
          'type': str,
          'help': 'Help text for the parameter',
          'default': 'composer',
      },
  }

  def build_tree(self):
    """Construct the diagnostic tree with steps."""
    start = EnvCreationStart()
    env_creation_gateway = EnvCreationGateway()
    iam_permission_check = IAMPermissionCheck()
    shared_vpc_iam_check = SharedVPCIAMCMEKCheck()
    encryption_config_checker = EncryptionConfigChecker()
    log_based_checks = LogBasedChecks()

    self.add_start(step=start)
    self.add_step(parent=start, child=env_creation_gateway)
    self.add_step(parent=env_creation_gateway, child=iam_permission_check)
    self.add_step(parent=iam_permission_check, child=shared_vpc_iam_check)
    self.add_step(parent=shared_vpc_iam_check, child=encryption_config_checker)
    self.add_step(parent=encryption_config_checker, child=log_based_checks)
    self.add_end(EnvCreationEnd())


class EnvCreationStart(runbook.StartStep):
  """Initiates Composer environment creation and performs project validation.

  This class serves as the starting point for a Composer runbook, handling the
  following tasks:

  1. Project Retrieval and Logging:
      - Obtains project details using the provided `project_id`.
      - Logs essential project information (ID and number) for visibility.

  2. Product Identification:
      - Extracts the product name based on the module structure.
      - Stores the product name in a Product flag (`PRODUCT_FLAG`) for reference
      in subsequent steps.

  3. Project Name and ID Validation:
      - Checks if the project's name and ID are identical.
      - Logs an "OK" status if they match.
      - Logs a "failed" status if they differ, but suggests remediation by
      entering 'c' to continue (as this is often acceptable).

  Attributes: None

  Methods:
      execute(self): The main entry point for executing the environment creation
      and validation logic.
  """

  def execute(self):
    """Starting composer runbook for environment creation."""
    project_id = op.get(flags.PROJECT_ID)

    project = crm.get_project(project_id)
    op.info('Project Details:')
    op.info(f'  Project ID: {project.id}')
    op.info(f'  Project Number: {project.number}')

    product = self.__module__.split('.')[-2]
    op.put(PRODUCT_FLAG, product)


class EnvCreationGateway(runbook.Step):
  """Selects a Composer environment and service account for troubleshooting.

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
  """

  def execute(self):
    """Checking Number of Composer environments in the project."""

    if op.get(PRODUCT_FLAG) == 'composer':
      # num = len(composer.get_environments(op.context))
      # op.info(f'Composer Environment:{num}')
      op.info('Please select the environment you want to troubleshoot.')

    environments = composer.get_environments(op.context)

    if not environments:
      op.add_failed(
          resource=None,
          reason='No Composer environments found in the project.',
          remediation=(
              'No Composer environments found in the project. Please try'
              ' creating a Composer environment and try again.'),
      )
      return

    op.info('Environment Selection::')
    for i, env in enumerate(environments):
      op.info(f'{i+1}. (Env Name: {env.name}) (Region: {env.region})(Network'
              f' Details : {env.network_details})')

    while True:
      try:
        choice = int(
            input('Please enter the number of the environment you want to'
                  ' troubleshoot : '))
        if choice < 1 or choice > len(environments):
          op.add_failed(
              None,
              reason='Invalid choice. Please enter a number from the list.',
              remediation='Please try again.',
          )
        else:
          break
      except ValueError:
        op.info('Invalid input. Please enter a number.')

    selected_env = environments[choice - 1]
    op.put('selected_composer_env', selected_env)

    while True:
      op.info('Service Account::')
      use_env_sa = input("Use the environment's default service account"
                         f' ({selected_env.service_account})? (y/n): ').lower()
      if use_env_sa not in ('y', 'n'):
        op.add_failed(
            None,
            reason="Invalid input. Please enter 'y' or 'n'.",
            remediation='Please try again.',
        )
      else:
        break

    service_account = (selected_env.service_account
                       if use_env_sa == 'y' else None)
    if not service_account:
      while True:
        service_account = input('Enter the service account: ')
        if not re.match(r'[^@]+@[^@]+\.[^@]+', service_account):
          op.add_failed(
              None,
              reason='Invalid service account. Please try again.',
              remediation='Please try again.',
          )
        else:
          break

    op.put('selected_service_account', service_account)


class IAMPermissionCheck(runbook.Step):
  """Verifies IAM permissions for Google Cloud Composer service accounts.

  This class performs a comprehensive check of the IAM (Identity and Access
  Management)
  permissions assigned to essential service accounts utilized by Google Cloud
  Composer.
  It ensures that these accounts possess the necessary roles to interact with
  Google
  Cloud resources and perform their intended functions within the Composer
  environment.

  Attributes: None

  Methods:
      execute(self):
          Initiates the IAM permission check for all specified service accounts.
      _check_iam_permissions(self, project_id, service_account, required_role,
      account_description):
          Helper function to verify IAM permissions for a specific service
          account and role.
      Raises:
      Exception: If an error occurs during the IAM permission check process,
      it's logged and
                 an appropriate failure message is added to the runbook
                 operation.
  """

  def execute(self):
    """Validating IAM permissions for all service accounts involved
    in the Composer environment creation."""

    project_id = op.context.project_id
    proj = crm.get_project(op.get(flags.PROJECT_ID))

    service_accounts_to_check = {
        'selected_service_account': {
            'name': op.get('selected_service_account'),
            'role': 'roles/editor',
            'description': "Composer environment's default service account",
        },
        'composer_service_agent': {
            'name':
                f'service-{proj.number}@cloudcomposer-accounts.iam.gserviceaccount.com',
            'role':
                'roles/composer.ServiceAgentV2Ext',
            'description':
                'Composer Service Agent',
        },
        'cloud_build_sa': {
            'name': f'{proj.number}@cloudbuild.gserviceaccount.com',
            'role': 'roles/cloudbuild.builds.builder',
            'description': 'Cloud Build Service Account',
        },
        'goog_api_sa': {
            'name': f'{proj.number}@cloudservices.gserviceaccount.com',
            'role': 'roles/editor',
            'description': 'Google APIs service account',
        },
    }

    for _, account_info in service_accounts_to_check.items():
      if not account_info['name']:
        continue

      self._check_iam_permissions(
          project_id,
          account_info['name'],
          account_info['role'],
          account_info['description'],
      )

  def _check_iam_permissions(self, project_id, service_account, required_role,
                             account_description):
    """Helper function to check IAM permissions for a specific service account and role."""

    try:
      iam_policy = iam.get_project_policy(project_id)

      if not iam.is_service_account_enabled(service_account, project_id):
        op.add_failed(
            None,
            reason=(
                f'The {account_description} {service_account} is disabled or'
                ' deleted.'),
            remediation=(
                f'The {account_description} {service_account} used by Composer'
                f' should have the {required_role} role.'),
        )
      elif not iam_policy.has_role_permissions(
          f'serviceAccount:{service_account}', required_role):
        op.add_failed(
            iam_policy,
            reason=(
                f'The {account_description}: {service_account} is missing role:'
                f' {required_role}.'),
            remediation=(f'Please grant the role: {required_role} to the'
                         f' {account_description}: {service_account}.'),
        )
      else:
        op.add_ok(
            iam_policy,
            reason=(f'{account_description}: {service_account} has the correct'
                    f' {required_role}.'),
        )
    except Exception as e:
      logging.exception('An error occurred while checking IAM permissions:')
      op.add_failed(
          iam_policy,
          reason=f'Error checking IAM roles: {e}',
          remediation='Please investigate and resolve the error.',
      )


class EncryptionConfigChecker(runbook.Step):
  """Checks the permissions of the KMS key used for encryption in Composer env.

  This class performs the following checks:

  1. **CMEK Configuration:** Verifies if Customer-Managed Encryption Keys (CMEK)
  are enabled for the selected Cloud Composer environment. CMEK provides
  enhanced security by allowing you to manage encryption keys within your own
  Google Cloud project.

  2. **IAM Permissions:** If CMEK is enabled, it checks whether the necessary
  Google Cloud service accounts have the required permissions
  (`cloudkms.cryptoKeyEncrypterDecrypter`) to use the KMS key. These permissions
  are crucial for successful encryption and decryption operations.

  Attributes: None

  Methods:
      check_kms_key_permissions(project_id, key_name):
          Validates the IAM permissions of the specified KMS key.

      execute():
          Retrieves the Cloud Composer environment configuration and initiates
          the KMS key checks.

  Raises:
      AttributeError: If the KMS key configuration is missing or unexpected.
      Exception: For any other unexpected errors encountered during the checks.

  Note:
      This class assumes that the Cloud Composer environment configuration is
      available in the `op` object (presumably an operation context).

  Example Usage:
      checker = EncryptionConfigChecker()
      checker.execute()
  """

  def check_kms_key_permissions(self, project_id, key_name):
    try:
      key_policy = kms.get_crypto_key_iam_policy(key_name)

      proj = crm.get_project(op.get(flags.PROJECT_ID))
      kms_role = 'roles/cloudkms.cryptoKeyEncrypterDecrypter'
      iam_policy = iam.get_project_policy(project_id)
      service_account_list = [
          f'service-{proj.number}@cloudcomposer-accounts.iam.gserviceaccount.com',
          f'service-{proj.number}@compute-system.iam.gserviceaccount.com',
          f'service-{proj.number}@gcp-sa-artifactregistry.iam.gserviceaccount.com',
          f'service-{proj.number}@gcp-sa-pubsub.iam.gserviceaccount.com',
          f'service-{proj.number}@container-engine-robot.iam.gserviceaccount.com',
      ]

      for sa in service_account_list:
        if not iam.is_service_account_enabled(sa, project_id):
          op.add_failed(
              None,
              reason=(f'Service account {sa} is disabled or deleted in project'
                      f' {project_id}'),
              remediation=(f'Please enable or add the Service Account {sa} in'
                           f' project {project_id}'),
          )
        elif not key_policy.has_role_permissions(
            f'serviceAccount:{sa}',
            kms_role) or iam_policy.has_role_permissions(
                f'serviceAccount:{sa}', kms_role):
          op.add_failed(
              iam_policy,
              reason=(
                  f'Service account {sa} is missing role: {kms_role} at project'
                  ' level and at key level'),
              remediation=(f'Please grant the role: {kms_role} to the service'
                           f' account: {sa} at project level or at key level'),
          )
        else:
          op.add_ok(
              iam_policy,
              reason=(
                  f'Service account: {sa} has the correct'
                  f' {kms_role} permission at project level or at key level'),
          )

    except Exception as e:
      logging.exception('Error checking IAM permissions:')
      op.add_failed(
          iam_policy,
          reason=f'Error checking IAM roles: {e}',
          remediation='Please investigate and resolve the error.',
      )

  def execute(self):
    """Checking if a Customer-Managed Encryption Key (CMEK) is enabled,
    for this Composer environment and verifying necessary permissions..."""
    selected_env = op.get('selected_composer_env')
    if selected_env:
      try:
        key_name = selected_env.kms_key_name
        project_id = op.context.project_id
        if key_name and key_name != 'No KMS key found':
          op.info(
              'Customer-Managed Key (CMEK) detected. Verifying permissions for'
              ' the configured KMS key...')
          self.check_kms_key_permissions(project_id, key_name)
        else:
          op.info('CMEK key is NOT configured! Skipping permission check...')
      except AttributeError:
        op.info('KMS key configuration not found. Skipping permission check...')


class SharedVPCIAMCMEKCheck(runbook.Step):
  """A class to check IAM permissions for Composer environments in Shared VPCs.

  This class verifies whether a Google Cloud Composer environment is configured
  with Shared VPC and, if so, checks the necessary IAM permissions for the
  relevant service accounts. It reports the status of each check (success or
  failure) along with remediation steps for any failed checks.
  """

  def get_environment_network(self, project_id, selected_env):
    """Retrieves network details and determines if Shared VPC is in use."""
    if not selected_env.network_details:
      op.info('Skipping IAM checks due to missing network details.')
      return None, None

    match = re.search(pattern=r'projects/([^/]+)/',
                      string=selected_env.network_details)
    if match:
      host_project_id = match.group(1)
    else:
      host_project_id = None

    if host_project_id is None:  # added a check for composer 3.
      op.info('Selected Composer 3 environment is not using Shared VPC:'
              f' {selected_env.name}')
      return None, None
    elif host_project_id == project_id:
      op.info('Selected Composer environment is not using Shared VPC:'
              f' {selected_env.name}')
      return None, None
    else:
      op.info('SHARED VPC DETECTED')
      return selected_env.network_details, host_project_id

  def _get_service_accounts(self, project, host_project_id=None):
    """Builds a dictionary of service accounts to check based on Shared VPC usage."""
    if host_project_id is None:  # Not using Shared VPC
      return {}
    service_accounts = {
        'google_apis_service_account': {
            'name': f'{project.number}@cloudservices.gserviceaccount.com',
            'role': 'roles/compute.networkUser',
            'description': 'Google APIs service account',
        },
        'service_project_gke_service_account': {
            'name':
                f'service-{project.number}@container-engine-robot.iam.gserviceaccount.com',
            'role': [
                'roles/container.hostServiceAgentUser',
                'roles/compute.networkUser',
            ],
            'description':
                'Service project GKE service account',
        },
        'composer_service_agent': {
            'name':
                f'service-{project.number}@cloudcomposer-accounts.iam.gserviceaccount.com',
            'role': [
                'roles/composer.sharedVpcAgent',
                'roles/compute.networkUser',
            ],
            'description':
                'Composer Service Agent',
        },
    }

    if host_project_id:
      host_proj_number = crm.get_project(host_project_id).number
      service_accounts['host_project_gke_service_account'] = {
          'name':
              f'service-{host_proj_number}@container-engine-robot.iam.gserviceaccount.com',
          'role':
              'roles/container.serviceAgent',
          'description':
              'Host project GKE service account',
      }

    return service_accounts

  def execute(self):
    """Checking if the Composer environment is,
    configured to use a Shared VPC and verifying necessary permissions..."""
    project_id = op.get(flags.PROJECT_ID)
    project = crm.get_project(project_id)
    selected_env = op.get('selected_composer_env')
    network_details, host_project_id = self.get_environment_network(
        project_id, selected_env)
    service_accounts_to_check = self._get_service_accounts(
        project, host_project_id)

    if host_project_id:
      op.info(f'  Host Project ID: {host_project_id}')
    elif network_details is not None:
      op.info(f'No Shared VPC found for environment {selected_env.name}.')

    for _, account_info in service_accounts_to_check.items():
      self._check_iam_permissions(
          host_project_id if host_project_id else project_id,
          account_info['name'],
          account_info['role'],
          account_info['description'],
      )

  def _check_iam_permissions(self, project_id, service_account, required_role,
                             account_description):
    """Helper function to check IAM permissions."""

    try:
      # Fetch the IAM policy for the specified project
      iam_policy = iam.get_project_policy(project_id)

      # Check if the service account is enabled in the project
      if not iam.is_service_account_enabled(service_account, project_id):
        op.add_failed(
            None,  # No policy to reference, as the account doesn't exist
            reason=(
                f'The {account_description} {service_account} is disabled or'
                ' deleted.'),
            remediation=(
                f'The {account_description} {service_account} used by Composer'
                f' should have the {" or ".join(required_role)} roles.'),
        )
      else:
        # Check if all required roles are present in the IAM policy
        if isinstance(required_role,
                      list):  # Handle multiple required roles (list)
          all_roles_found = True
          for role in required_role:
            if not iam_policy.has_role_permissions(
                f'serviceAccount:{service_account}', role):
              op.add_failed(
                  iam_policy,
                  reason=(
                      f'The {account_description}: {service_account} is missing'
                      f' role: {role}.'),
                  remediation=(f'Please grant the role: {role} to the'
                               f' {account_description}: {service_account}.'),
              )
              all_roles_found = False
              break  # Exit the loop if any role is missing
          if all_roles_found:
            op.add_ok(
                iam_policy,
                reason=(f'{account_description}: {service_account} has all the'
                        ' correct permissions.'),
            )
        else:  # Handle a single required role (string)
          if not iam_policy.has_role_permissions(
              f'serviceAccount:{service_account}', required_role):
            op.add_failed(
                iam_policy,
                reason=(
                    f'The {account_description}: {service_account} is missing'
                    f' role: {required_role}.'),
                remediation=(f'Please grant the role: {required_role} to the'
                             f' {account_description}: {service_account}.'),
            )
          else:
            op.add_ok(
                iam_policy,
                reason=(
                    f'{account_description}: {service_account} has the correct'
                    f' {required_role} permission.'),
            )

    # Catch any exceptions that might occur during the IAM permission check
    except Exception as e:  # pylint: disable=broad-except
      logging.exception('An error occurred while checking IAM permissions:')
      op.add_failed(
          iam_policy,
          reason=f'Error checking IAM roles: {e}',
          remediation='Please investigate and resolve the error.',
      )


class LogBasedChecks(runbook.Step):
  """The LogBasedChecks class is a designed to scrutinize (GCP) logs for

  specific operational issues.

  It primarily checks for:

  Org Policy Violations: It examines logs for instances where organizational
  policies, such as those related to compute instance configuration (e.g.,
  serial port logging, OS login, IP forwarding), have been breached.

  Managed Instance Group Quota Issues: It investigates whether any logs indicate
  that the project has exceeded its allocated quota for creating managed
  instance groups.

  The class provides structured output, adding success messages if no issues are
  found and failure messages with remediation suggestions if problems are
  detected. This aids in automating the monitoring and troubleshooting of common
  GCP operational challenges.
  """

  def execute(self):
    """Checking for org policy violations and Managed Instance Group quota,
    related issues in logs checks."""
    project_id = op.get(flags.PROJECT_ID)

    self._check_org_policy_violations(project_id)
    self._check_managed_instance_group_quota(project_id)
    self._check_caller_does_not_have_permission(project_id)

  def _check_org_policy_violations(self, project_id):
    """Checks for org policy violation logs."""
    filter_str = (
        'protoPayload.status.message=~"Constraint .* violated" AND'
        ' ("compute.disableSerialPortLogging" OR "compute.requireOsLogin" OR'
        ' "compute.vmCanIpForward" OR "compute.requireShieldedVm" OR'
        ' "constraints/compute.vmExternalIpAccess" OR'
        ' "compute.restrictVpcPeering") AND'
        ' protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"'
        ' AND severity=ERROR')

    log_entries = logs.query(
        project_id=project_id,
        resource_type='',
        log_name='',
        filter_str=filter_str,
    )

    if log_entries:
      op.add_ok(
          None,
          reason=f'No Org Policy Violation detected for {project_id} 😎. Nice!',
      )
    else:
      op.add_failed(
          None,
          reason=f'Org Policy Violation detected for {project_id}🚀',
          remediation=f'Kindly review the Org Policy for {project_id}',
      )

  def _check_managed_instance_group_quota(self, project_id):
    """Checks for Managed Instance Group quota exceeded logs."""
    filter_str = (
        'jsonPayload.message:"googleapi: Error 403: Insufficient regional quota'
        ' to satisfy request:" severity>=WARNING')

    log_entries = logs.query(
        project_id=project_id,
        resource_type='',
        log_name='',
        filter_str=filter_str,
    )

    if log_entries:
      op.add_ok(
          None,
          reason=(
              f'Managed Instance Group Quota within limits for {project_id} 😎.'
              ' Nice!'),
      )
    else:
      op.add_failed(
          None,
          reason=f'Managed Instance Group Quota exceeded for {project_id}🚀',
          remediation=(
              f'Kindly review the Managed Instance Group Quota for {project_id}'
          ),
      )

  def _check_caller_does_not_have_permission(self, project_id):
    """Checks for Caller does not have permission."""
    filter_str = 'The caller does not have permission'

    log_entries = logs.query(
        project_id=project_id,
        resource_type='',
        log_name='',
        filter_str=filter_str,
    )

    if log_entries:
      op.add_ok(
          None,
          reason=f'No caller permission issues detected {project_id} 😎. Nice!',
      )
    else:
      op.add_failed(
          None,
          reason=f'Caller permission issue detected for {project_id}🚀',
          remediation=f'Kindly review the Caller permission for {project_id}',
      )


class EnvCreationEnd(runbook.EndStep):
  """RUNBOOK COMPLETED."""

  def execute(self):
    """✅ RUNBOOK COMPLETED ✅"""
    op.info(
        'Environment creation process finished. Review any warnings or errors'
        ' for further action.')
