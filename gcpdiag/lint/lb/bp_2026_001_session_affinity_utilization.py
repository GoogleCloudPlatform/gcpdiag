# Lint as: python3
"""Backend Services with Session Affinity should not use UTILIZATION balancing mode.

Description: Session affinity aims to send requests from the same client to
the same backend. Misconfiguration with balancing modes (especially using
UTILIZATION with session affinity) can lead to some backends being overloaded
while others are underutilized, or cause sessions to break unexpectedly. This
can negatively impact application performance and user experience.

When Session Affinity is enabled (e.g., CLIENT_IP, GENERATED_COOKIE,
HTTP_COOKIE),
the load balancer attempts to direct requests from the same client to the same
backend.
However, UTILIZATION mode distributes traffic based on the current utilization
of backends.
This can conflict, causing the load balancer to prioritize utilization targets
over
session affinity.

It is recommended to use RATE (for HTTP/S) or CONNECTION (for TCP/SSL)
balancing modes when Session Affinity is required.
"""

from gcpdiag import lint, models
from gcpdiag.queries import lb


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  try:
    backend_services = lb.get_backend_services(context.project_id)
  except Exception as e:
    report.add_skipped(None, f'Failed to query backend services: {e}')
    return

  if not backend_services:
    report.add_skipped(None, 'No backend services found in project')
    return

  for bs in backend_services:
    if bs.session_affinity != 'NONE':
      has_utilization_mode = False
      if bs.backends:
        for backend in bs.backends:
          if backend.get('balancingMode') == 'UTILIZATION':
            has_utilization_mode = True
            break

      if has_utilization_mode:
        report.add_failed(
          bs,
          f'Backend Service [{bs.name}] has session affinity'
          f" '{bs.session_affinity}' and uses UTILIZATION balancing mode in"
          ' one or more of its backend groups. This can break session'
          ' affinity. Consider using RATE or CONNECTION mode instead.',
        )
      else:
        # Session affinity is enabled, but no UTILIZATION mode found
        report.add_ok(bs)
    else:
      # Session affinity is NONE, so the rule is not applicable
      report.add_ok(bs)
