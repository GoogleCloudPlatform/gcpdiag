# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module containing steps to analyze SSL certificate issues."""

from datetime import datetime, timedelta
from typing import List, Union

import googleapiclient.errors
from boltons.iterutils import get_path

from gcpdiag import config, runbook
from gcpdiag.queries import apis, crm, dns, lb, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.lb import flags

TargetProxy = Union[lb.TargetHttpsProxy, lb.TargetSslProxy]


class SslCertificates(runbook.DiagnosticTree):
  """This runbook diagnoses and troubleshoots issues with SSL certificates.

  The supported certificates are Google-managed classic certificates attached to
  load balancers.

  It helps identify and resolve common problems that prevent certificates from
  provisioning or functioning correctly.

  Key Investigation Area:

  - Certificate Status:
    - Checks the certificate's provisioning status and identifies any failed
    domains.
  - Domain Validation:
    - Verifies DNS configuration for each domain, ensuring proper A/AAAA records
    and the absence of conflicting records.
  - Load Balancer Configuration:
    - Confirms the certificate is correctly attached to a target proxy and
    associated with a forwarding rule using port 443.
  - Conflicting resources:
    - Ensures no certificate map is attached to the target proxy, which can
    interfere with Google-managed certificates.
  - Provisioning Time:
    - Checks Cloud Logging to determine when the certificate was attached and
    allows sufficient time for propagation.
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True,
      },
      flags.CERTIFICATE_NAME: {
          'type': str,
          'help': 'The name of the SSLcertificate that you want to investigate',
          'required': True,
      },
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate your step classes
    start = SslCertificatesStart()
    # add them to your tree
    self.add_start(start)
    # you can create custom steps to define unique logic
    cert_status = AnalyzeCertificateStatus()
    # Describe the step relationships
    self.add_step(parent=start, child=cert_status)
    self.add_step(parent=cert_status, child=AnalyzeDomainStatuses())
    # Ending your runbook
    self.add_end(SslCertificatesEnd())


class SslCertificatesStart(runbook.StartStep):
  """Verifies the existence type and status of the SSL certificate."""

  template = 'ssl_certificates::confirmation'

  def execute(self):
    """Verifies the existence type and status of the SSL certificate."""
    proj = crm.get_project(op.get(flags.PROJECT_ID))

    if not apis.is_enabled(op.context.project_id, 'compute'):
      op.add_skipped(proj, reason='Compute API is not enabled')
      return  # Early exit if Compute API is disabled

    try:
      op.info(f'name: {op.get(flags.CERTIFICATE_NAME)}')
      certificate = lb.get_ssl_certificate(op.context.project_id,
                                           op.get(flags.CERTIFICATE_NAME))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          proj,
          reason=op.prep_msg(
              op.SKIPPED_REASON,
              name=op.get(flags.CERTIFICATE_NAME),
              project_id=op.get(flags.PROJECT_ID),
          ),
      )
      return  # Early exit if certificate doesn't exist
    if certificate.type == 'SELF_MANAGED':
      op.add_skipped(
          proj,
          reason=op.prep_msg(op.SKIPPED_REASON_ALT1,
                             name=op.get(flags.CERTIFICATE_NAME)),
      )
      return  # Early exit if certificate is not Google-managed

    if certificate.status == 'ACTIVE':
      op.add_ok(
          proj,
          reason=op.prep_msg(op.SUCCESS_REASON,
                             name=op.get(flags.CERTIFICATE_NAME)),
      )
    else:
      op.add_failed(proj,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       name=op.get(flags.CERTIFICATE_NAME)),
                    remediation='')


class AnalyzeCertificateStatus(runbook.Gateway):
  """Checks the status of the Google-managed certificate."""

  template = 'ssl_certificates::cert_status'

  def execute(self):
    """Checks the status of the Google-managed certificate."""
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))
    op.add_metadata('certificateStatus', certificate.status)

    if certificate.status == 'PROVISIONING_FAILED_PERMANENTLY':
      op.add_failed(
          certificate,
          reason=op.prep_msg(op.FAILURE_REASON,
                             name=op.get(flags.CERTIFICATE_NAME)),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return
    elif certificate.status in ('PROVISIONING_FAILED', 'PROVISIONING'):
      op.add_uncertain(
          certificate,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON,
              name=op.get(flags.CERTIFICATE_NAME),
              status=certificate.status,
              context=('Further investigation into the status of each domain is'
                       ' necessary.'),
          ),
      )
      return
    elif certificate.status == 'RENEWAL_FAILED':
      op.add_uncertain(
          certificate,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON,
              name=op.get(flags.CERTIFICATE_NAME),
              status=certificate.status,
              context=(
                  'This typically occurs when the load balancer or DNS'
                  ' configuration has issues, preventing the automatic renewal'
                  ' of the Google-managed certificate.'),
          ),
      )
      return

    op.add_ok(
        certificate,
        reason=op.prep_msg(
            op.SUCCESS_REASON,
            name=op.get(flags.CERTIFICATE_NAME),
            status=certificate.status,
        ),
    )


class AnalyzeDomainStatuses(runbook.Gateway):
  """Checks the status of each individual domain associated with the SSL certificate."""

  template = 'ssl_certificates::domain_status'

  def execute(self):
    """Checks the status of each individual domain associated with the SSL certificate."""
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))

    failed_not_visible_domains = []
    failed_caa_domains = []
    failed_rate_limited_domains = []
    provisioning_domains = []
    for domain, status in certificate.domain_status.items():
      if status == 'FAILED_NOT_VISIBLE':
        failed_not_visible_domains.append(domain)
      if status in ('FAILED_CAA_CHECKING', 'FAILED_CAA_FORBIDDEN'):
        failed_caa_domains.append(domain)
      if status == 'FAILED_RATE_LIMITED':
        failed_rate_limited_domains.append(domain)
      if status == 'PROVISIONING':
        provisioning_domains.append(domain)

    if failed_not_visible_domains:
      step = AnalyzeFailedNotVisibleDomains()
      step.domains = failed_not_visible_domains
      self.add_child(step)
    if failed_caa_domains:
      step = AnalyzeFailedCaaCheck()
      step.domains = failed_caa_domains
      self.add_child(step)
    if failed_rate_limited_domains:
      step = AnalyzeRateLimitedDomains()
      step.domains = failed_rate_limited_domains
      self.add_child(step)
    if provisioning_domains:
      step = AnalyzeProvisioningDomains()
      step.domains = provisioning_domains
      self.add_child(step)
    if failed_not_visible_domains or provisioning_domains:
      self.add_child(CheckCertificateAttachment())
    if (not failed_not_visible_domains and not failed_caa_domains and
        not failed_rate_limited_domains and not provisioning_domains):
      op.add_ok(
          certificate,
          reason=op.prep_msg(op.SUCCESS_REASON,
                             name=op.get(flags.CERTIFICATE_NAME)),
      )


class AnalyzeFailedNotVisibleDomains(runbook.Step):
  """Analyzes domains in "FAILED_NOT_VISIBLE" state."""

  template = 'ssl_certificates::failed_not_visible_domains'

  domains: List[str]

  def execute(self):
    """Analyzes domains in "FAILED_NOT_VISIBLE" state."""
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))
    op.add_failed(
        certificate,
        reason=op.prep_msg(
            op.FAILURE_REASON,
            domains=', '.join(self.domains),
        ),
        remediation='',
    )
    op.add_metadata('failedNotVisibleDomains', self.domains)


class AnalyzeProvisioningDomains(runbook.Step):
  """Analyzes domains in "PROVISIONING" state."""

  template = 'ssl_certificates::provisioning_domains'

  domains: List[str]

  def execute(self):
    """Analyzes domains in "PROVISIONING" state."""
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))
    op.add_uncertain(
        certificate,
        reason=op.prep_msg(
            op.UNCERTAIN_REASON,
            domains=', '.join(self.domains),
        ),
        remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION),
    )
    op.add_metadata('provisioningDomains', self.domains)


class AnalyzeRateLimitedDomains(runbook.Step):
  """Analyzes domains in "FAILED_RATE_LIMITED" state."""

  template = 'ssl_certificates::failed_rate_limited_domains'

  domains: List[str]

  def execute(self):
    """Analyzes domains in "FAILED_RATE_LIMITED" state."""
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))
    op.add_failed(
        certificate,
        reason=op.prep_msg(op.FAILURE_REASON, domains=', '.join(self.domains)),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
    )
    op.add_metadata('failedRateLimitedDomains', self.domains)


class AnalyzeFailedCaaCheck(runbook.Step):
  """Analyzes domains in "FAILED_CAA_CHECKING" or "FAILED_CAA_FORBIDDEN" state."""

  template = 'ssl_certificates::failed_caa_check_domains'

  domains: List[str]

  def execute(self):
    """Analyzes domains in "FAILED_CAA_CHECKING" or "FAILED_CAA_FORBIDDEN" state."""
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))
    op.add_failed(
        certificate,
        reason=op.prep_msg(op.FAILURE_REASON, domains=', '.join(self.domains)),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
    )
    op.add_metadata('failedCaaCheckDomains', self.domains)


class CheckCertificateAttachment(runbook.Gateway):
  """Checks if the SSL certificate is attached to a target proxy.

  This target proxy needs to be in use by a forwarding rule for the provisioning
  to succeed.
  """

  template = 'ssl_certificates::check_certificate_attachment'

  def execute(self):
    """Checks if the SSL certificate is attached to a target proxy."""
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))

    try:
      target_https_proxies = lb.get_target_https_proxies(op.context.project_id)
      target_ssl_proxies = lb.get_target_ssl_proxies(op.context.project_id)
    except googleapiclient.errors.HttpError as e:
      op.add_skipped(
          certificate,
          reason=f'Target proxies could not be fetched: {e}',
      )
      return

    target_proxies_with_certificate = []
    for target_proxy in target_https_proxies + target_ssl_proxies:
      if certificate.self_link in target_proxy.ssl_certificates:
        target_proxies_with_certificate.append(target_proxy)

    if not target_proxies_with_certificate:
      op.add_failed(
          certificate,
          reason=op.prep_msg(op.FAILURE_REASON,
                             name=op.get(flags.CERTIFICATE_NAME)),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return

    try:
      forwarding_rules = lb.get_forwarding_rules(op.context.project_id)
    except ValueError as e:
      op.add_skipped(
          certificate,
          reason=f'Target proxies could not be fetched: {e}',
      )
      return

    forwarding_rules_by_target_proxy = {}
    for fr in forwarding_rules:
      forwarding_rules_by_target_proxy.setdefault(fr.target, []).append(fr)

    # Filter out target proxies that are not in use by any forwarding rules
    used_target_proxies_with_certificate = [
        tp for tp in target_proxies_with_certificate
        if forwarding_rules_by_target_proxy.get(tp.full_path)
    ]

    if not used_target_proxies_with_certificate:
      op.add_failed(
          certificate,
          reason=
          ('The SSL certificate is attached to target proxies:'
           f" {', '.join([tp.full_path for tp in target_proxies_with_certificate])} that"
           ' are not in use by any forwarding rules.'),
          remediation='Please attach the target proxies to forwarding rules',
      )
      return

    # Gather forwarding rules that use target proxies with the given certificate
    forwarding_rules_with_certificate = []
    for tp in used_target_proxies_with_certificate:
      rules = forwarding_rules_by_target_proxy.get(tp.full_path)
      if rules:
        forwarding_rules_with_certificate.extend(rules)

    op.add_ok(
        certificate,
        reason=op.prep_msg(
            op.SUCCESS_REASON,
            name=op.get(flags.CERTIFICATE_NAME),
            target_proxies=', '.join(
                [tp.full_path for tp in used_target_proxies_with_certificate]),
        ),
    )

    for domain in certificate.domain_status.keys():
      if certificate.domain_status[domain] != 'ACTIVE':
        verify_dns_records = VerifyDnsRecords()
        verify_dns_records.domain = domain
        verify_dns_records.certificate_name = op.get(flags.CERTIFICATE_NAME)
        verify_dns_records.forwarding_rules_with_certificate = (
            forwarding_rules_with_certificate)
        self.add_child(verify_dns_records)

    verify_forwarding_rules_port = VerifyForwardingRulesPort()
    verify_forwarding_rules_port.forwarding_rules_with_certificate = (
        forwarding_rules_with_certificate)
    self.add_child(verify_forwarding_rules_port)

    verify_no_certificate_map_conflict = VerifyNoCertificateMapConflict()
    verify_no_certificate_map_conflict.target_proxies_with_certificate = (
        target_proxies_with_certificate)
    self.add_child(verify_no_certificate_map_conflict)

    check_provisioning_time = CheckProvisioningTime()
    check_provisioning_time.target_proxies_with_certificate = (
        target_proxies_with_certificate)
    check_provisioning_time.forwarding_rules_with_certificate = (
        forwarding_rules_with_certificate)
    self.add_child(check_provisioning_time)


class VerifyDnsRecords(runbook.Gateway):
  """Checks the DNS records for specific domain associated with the SSL certificate."""

  template = 'ssl_certificates::verify_dns_records'

  forwarding_rules_with_certificate: List[lb.ForwardingRules]
  domain: str
  certificate_name: str

  @property
  def execution_message(self):
    return (
        f'Checks the DNS records for domain "{self.domain}" associated with the'
        f' SSL certificate "{self.certificate_name}".')

  def execute(self):
    certificate_name = op.get(flags.CERTIFICATE_NAME)
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         certificate_name)
    ip_addresses = dns.find_dns_records(self.domain)

    op.add_metadata('domain', self.domain)
    op.add_metadata('domain_to_ip_addresses', ip_addresses)

    # Group forwarding rules by IP address
    frs_by_ip = {}
    for fr in self.forwarding_rules_with_certificate:
      frs_by_ip.setdefault(fr.ip_address, []).append(fr)

    # Check which IP addresses point to the load balancer
    ip_addresses_pointing_to_lb = []
    unresolved_ip_addresses = []
    for ip_address in ip_addresses:
      if frs_by_ip.get(ip_address):
        ip_addresses_pointing_to_lb.append(ip_address)
      else:
        unresolved_ip_addresses.append(ip_address)

    if ip_addresses_pointing_to_lb and not unresolved_ip_addresses:
      op.add_ok(
          certificate,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              domain=self.domain,
              ip_addresses=', '.join(ip_addresses_pointing_to_lb),
              name=op.get(flags.CERTIFICATE_NAME),
          ),
      )
    elif ip_addresses_pointing_to_lb and unresolved_ip_addresses:
      op.add_uncertain(
          certificate,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON,
              domain=self.domain,
              name=op.get(flags.CERTIFICATE_NAME),
              unresolved_ip_addresses=', '.join(unresolved_ip_addresses),
              resolved_ip_addresses=', '.join(ip_addresses_pointing_to_lb),
          ),
          remediation=op.prep_msg(
              op.UNCERTAIN_REMEDIATION,
              domain=self.domain,
              name=op.get(flags.CERTIFICATE_NAME),
          ),
      )
    elif unresolved_ip_addresses:
      op.add_failed(
          certificate,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              domain=self.domain,
              unresolved_ip_addresses=', '.join(unresolved_ip_addresses),
              name=op.get(flags.CERTIFICATE_NAME),
          ),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              domain=self.domain,
              name=op.get(flags.CERTIFICATE_NAME),
          ),
      )
    else:
      op.add_failed(
          certificate,
          reason=op.prep_msg(op.FAILURE_REASON_ALT1, domain=self.domain),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              domain=self.domain,
              name=op.get(flags.CERTIFICATE_NAME),
          ),
      )


class VerifyForwardingRulesPort(runbook.Step):
  """Checks if the load balancer is configured to listen on port 443.

  More specifically, check if all IP addresses associated with the certificate
  have forwarding rules that listen on port 443
  """

  template = 'ssl_certificates::verify_forwarding_rules_port'

  forwarding_rules_with_certificate: List[lb.ForwardingRules]

  def execute(self):
    """Checks if the load balancer is configured to listen on port 443."""
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))

    # Group forwarding rules by IP address
    frs_by_ip = {}
    for fr in self.forwarding_rules_with_certificate:
      frs_by_ip.setdefault(fr.ip_address, []).append(fr)

    misconfigured_entities = []
    # For each IP address check if the lb is configured to listen on port 443
    for ip_address, frs in frs_by_ip.items():
      if not any(self.is_port_in_range(443, fr.port_range) for fr in frs):
        misconfigured_entities.append(
            'The following forwarding rules with certificate'
            f' {certificate.name}: \n'
            f" {', '.join([fr.full_path for fr in frs])} \n use IP address"
            f' {ip_address} but none of them listen on port 443. \n')

    if misconfigured_entities:
      op.add_failed(
          certificate,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              misconfigured_entities='\n'.join(misconfigured_entities),
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                  name=op.get(flags.CERTIFICATE_NAME)),
      )
    else:
      op.add_ok(
          certificate,
          reason=op.prep_msg(op.SUCCESS_REASON,
                             name=op.get(flags.CERTIFICATE_NAME)),
      )

  def is_port_in_range(self, port: int, port_range: str):
    try:
      start, end = map(int, port_range.split('-'))
      return start <= port <= end
    except ValueError:
      # Handle invalid port range format
      return False


class VerifyNoCertificateMapConflict(runbook.Step):
  """Checks for conflicting certificate map set on a target proxy."""

  template = 'ssl_certificates::verify_no_certificate_map_conflict'

  target_proxies_with_certificate: List[TargetProxy]

  def execute(self):
    """Checks for conflicting certificate map set on a target proxy."""

    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))

    conflicting_target_proxies = []
    for target_proxy in self.target_proxies_with_certificate:
      if target_proxy.certificate_map:
        conflicting_target_proxies.append(target_proxy)

    if conflicting_target_proxies:

      target_proxy_conflicts = [
          f'Target Proxy: {target_proxy.full_path} has certificate map'
          f' {target_proxy.certificate_map} together with classic SSL'
          f" certificates {', '.join(target_proxy.ssl_certificates)}"
          for target_proxy in conflicting_target_proxies
      ]
      op.add_failed(
          certificate,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              conflicting_target_proxies='\n'.join(target_proxy_conflicts),
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(
          certificate,
          reason=op.prep_msg(op.SUCCESS_REASON,
                             name=op.get(flags.CERTIFICATE_NAME)),
      )


class CheckProvisioningTime(runbook.Step):
  """Checks if the SSL certificate associated resources has been updated recently."""

  template = 'ssl_certificates::check_provisioning_time'

  target_proxies_with_certificate: List[TargetProxy]
  forwarding_rules_with_certificate: List[lb.ForwardingRules]

  def execute(self):
    """Checks if the SSL certificate associated resources has been updated recently."""
    certificate = lb.get_ssl_certificate(op.context.project_id,
                                         op.get(flags.CERTIFICATE_NAME))

    recently_changed = []

    for forwarding_rule in self.forwarding_rules_with_certificate:
      filter_str = """resource.type="gce_forwarding_rule"
              resource.labels.region="{}"
              resource.labels.forwarding_rule_id="{}"
              protoPayload.methodName=~"(forwardingRules|globalForwardingRules).(patch|update|insert)"
              """.format(forwarding_rule.region, forwarding_rule.id)
      serial_log_entries = logs.realtime_query(
          project_id=op.get(flags.PROJECT_ID),
          filter_str=filter_str,
          start_time_utc=datetime.now() - timedelta(days=1),
          end_time_utc=datetime.now(),
      )

      if serial_log_entries:
        last_log = serial_log_entries.pop()
        timestamp = get_path(last_log, 'timestamp')
        recently_changed.append(
            f'Forwarding rule {forwarding_rule.name} in scope'
            f' {forwarding_rule.region} has been modified at {timestamp}.')

    for target_proxy in self.target_proxies_with_certificate:
      if target_proxy.region != 'global':
        # For now support only global target HTTPS proxies in this step
        # - there is no monitoring type for regional target proxies
        continue
      if isinstance(target_proxy, lb.TargetHttpsProxy):
        filter_str = """resource.type="gce_target_https_proxy"
                        resource.labels.target_https_proxy_id="{}"
                        protoPayload.methodName=~"targetHttpsProxies.(patch|update|insert|setSslCertificates)"
                        """.format(target_proxy.id)
      elif isinstance(target_proxy, lb.TargetSslProxy):
        filter_str = """resource.type="gce_target_ssl_proxy"
                        resource.labels.target_ssl_proxy_name="{}"
                        resource.labels.region="{}"
                        protoPayload.methodName=~"targetSslProxies.(patch|update|insert|setSslCertificates)"
                        """.format(target_proxy.region, target_proxy.name)
      else:
        # This should never happen
        raise ValueError(f'Unsupported target proxy type: {type(target_proxy)}')
      serial_log_entries = logs.realtime_query(
          project_id=op.get(flags.PROJECT_ID),
          filter_str=filter_str,
          start_time_utc=datetime.now() - timedelta(days=1),
          end_time_utc=datetime.now(),
      )

      if serial_log_entries:
        last_log = serial_log_entries.pop()
        timestamp = get_path(last_log, 'timestamp')
        recently_changed.append(
            f'Target proxy {target_proxy.name} in scope'
            f' {target_proxy.region} has been modified at {timestamp}.')

    if recently_changed:
      op.add_uncertain(
          certificate,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON,
              recently_changed='\n'.join(recently_changed),
              name=op.get(flags.CERTIFICATE_NAME),
          ),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION,
                                  name=op.get(flags.CERTIFICATE_NAME)),
      )
    else:
      op.add_ok(
          certificate,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              name=op.get(flags.CERTIFICATE_NAME),
          ),
      )


class SslCertificatesEnd(runbook.EndStep):
  """Concludes the SSL Certificate diagnostics process."""

  def execute(self):
    """Finalizing SSL Certificate diagnostics..."""
    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(
          kind=op.CONFIRMATION,
          message='Are you satisfied with the SSL Certificate troubleshooting?',
      )
      if response == op.NO:
        op.info(message=op.END_MESSAGE)
