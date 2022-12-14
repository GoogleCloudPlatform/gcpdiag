"""Explicit routes for Google APIs if the default route is modified.

If you need to modify the default route, then add explicit routes
for Google API destination IP ranges.

https://cloud.google.com/architecture/best-practices-vpc-design#explicit-routes

Note: This does not consider tagged routes or shadowed default routes.
Validate with a Connectivity Test.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, network


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  networks = network.get_networks(context.project_id)
  misconfigured_networks = ''
  if not networks:
    report.add_skipped(None, 'rule networks found')

  # Which networks have a subnet with PGA?
  pga_networks = {}
  for net in networks:
    for subnet in net.subnetworks.values():
      if subnet.is_private_ip_google_access():
        pga_networks[net.name] = 'missing'  # Starts with missing def route
        continue

  if not pga_networks:
    all_skipped = True  # There are no subnets with PGA, no need to run the rule

  else:
    all_skipped = False
    explicit_routes = ['199.36.153.8/30', '199.36.153.4/30']
    default_internet_gateway = 'default-internet-gateway'

    # Check the routes for the PGA networks
    routes = network.get_routes(context.project_id)
    for route in routes:
      current_network = route.network.split('/')[-1]
      if (route.dest_range == '0.0.0.0/0' and current_network in pga_networks):
        try:
          if route.next_hop_gateway.find(default_internet_gateway) != -1:
            pga_networks[current_network] = 'ok'
            continue  # OK: Next Hop for 0.0.0.0/0 is default-internet-gateway
        except KeyError:
          if pga_networks[current_network] != 'misconfig':
            pga_networks[current_network] = 'modified'
          # WARN:  Next Hop for 0.0.0.0/0 is NOT default-internet-gateway
          continue
      elif ((route.dest_range in explicit_routes) and
            (current_network in pga_networks)):
        try:
          if route.next_hop_gateway.find(default_internet_gateway) != -1:
            pga_networks[current_network] = 'ok'
            continue  # OK: Next Hop for PGA routes is default-internet-gateway
        except KeyError:
          # FAILED: Explicit routes not pointing to default gateway
          pga_networks[current_network] = 'misconfig'

    # Dump all the networks and their status
    for p_net, status in pga_networks.items():
      if status == 'modified':
        missing_text = 'might be missing explicit routes'
        misconfigured_networks += f' - Network: {p_net} -> {missing_text} \n'
        all_skipped = False
        continue
      elif status == 'misconfig':
        explicit_text = 'explicit routes not pointing to Default Internet \
Gateway'

        misconfigured_networks += f' - Network: {current_network} -> \
{explicit_text} \n'

      elif status == 'missing':
        missing_text = 'might be missing a default route for Google APIs'
        misconfigured_networks += f' - Network: {p_net} -> {missing_text} \n'
        all_skipped = False
        continue

  # Results
  text = 'The following networks have a modified default route and might \
be missing explicit routes to Google APIs:\n'

  if misconfigured_networks:
    report.add_failed(project, text + misconfigured_networks)
  else:
    report.add_ok(project)

  if all_skipped:
    report.add_skipped(project, 'no data')
