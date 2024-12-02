# Copyright 2024 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.googleapis.com/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""playbook to troubleshoot Application Load Balancer latency"""

import googleapiclient.errors

from gcpdiag import config, runbook
from gcpdiag.queries import apis, crm, lb, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.lb import flags


class Latency(runbook.DiagnosticTree):
  """This runbook diagnoses and troubleshoots latency issues with Application Load Balancers.

  It analyzes key metrics to identify potential bottlenecks and performance
  problems.

  Key Investigation Areas:

  - Backend Latency:
    - Measures the time taken for backends to respond to requests, checking if
    it exceeds a configurable threshold.
  - Request Count Per Second (QPS):
    - Monitors the rate of incoming requests to the load balancer, checking if
    it exceeds a configurable threshold.  A high request count coupled with high
    latency might suggest overload.
  - 5xx Error Rate:
    - Calculates the percentage of 5xx server errors, indicating problems on the
    backend servers.  This check uses a configurable threshold and considers the
    request count to provide a meaningful error rate.
  """

  parameters = {
      flags.PROJECT_ID: {
          "type": str,
          "help": "The Project ID where the load balancer is located",
          "required": True,
      },
      flags.FORWARDING_RULE_NAME: {
          "type": str,
          "help": ("The name of the forwarding rule associated with the Load"
                   " Balancer to check"),
          "required": True,
      },
      flags.REGION: {
          "type": str,
          "help": "The region where the forwarding rule is located",
          "required": False,
      },
      flags.BACKEND_LATENCY_THRESHOLD: {
          "type": float,
          "help": "Threshold for backend latency in milliseconds.",
          "required": False,
      },
      flags.REQUEST_COUNT_THRESHOLD: {
          "type": float,
          "help": "Threshold for average request count per second.",
          "required": False,
      },
      flags.ERROR_RATE_THRESHOLD: {
          "type": float,
          "help": "Threshold for error rate (percentage of 5xx errors).",
          "required": False,
      },
  }

  def build_tree(self):
    """Construct the diagnostic tree with start and end steps only."""
    start = LbLatencyStart()
    self.add_start(start)

    backend_latency_check = LbBackendLatencyCheck()
    self.add_step(parent=start, child=backend_latency_check)

    request_count_check = LbRequestCountCheck()
    self.add_step(parent=start, child=request_count_check)

    average_request_count = request_count_check.average_request_count
    error_rate_check = LbErrorRateCheck(
        average_request_count=average_request_count)
    self.add_step(parent=request_count_check, child=error_rate_check)

    self.add_end(LatencyEnd())


class LbLatencyStart(runbook.StartStep):
  """Fetch the specified forwarding rule"""

  def execute(self):
    """Fetch the specified forwarding rule."""
    proj = crm.get_project(op.get(flags.PROJECT_ID))

    if not apis.is_enabled(op.context.project_id, "compute"):
      op.add_skipped(proj, reason="Compute API is not enabled")
      return  # Early exit if Compute API is disabled

    try:
      # Attempt to fetch the forwarding rule
      self.forwarding_rule = lb.get_forwarding_rule(
          op.get(flags.PROJECT_ID), op.get(flags.FORWARDING_RULE_NAME),
          op.get(flags.REGION))
      op.info(f"Forwarding rule found: {self.forwarding_rule.name}")
    except googleapiclient.errors.HttpError:
      # Skip the runbook if forwarding rule is missing
      op.add_skipped(
          proj,
          reason="Forwarding rule not found in the specified project and region."
      )
      return

    load_balancer_type = self.forwarding_rule.load_balancer_type
    supported_load_balancer_types = [
        lb.LoadBalancerType.CLASSIC_APPLICATION_LB,
        lb.LoadBalancerType.GLOBAL_EXTERNAL_APPLICATION_LB,
        lb.LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB,
        lb.LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB,
    ]

    if load_balancer_type == lb.LoadBalancerType.LOAD_BALANCER_TYPE_UNSPECIFIED:
      op.add_skipped(
          proj,
          reason=(
              "The given forwarding rule type is not used for load balancing."),
      )
      return
    elif load_balancer_type not in supported_load_balancer_types:
      op.add_skipped(
          proj,
          reason=(
              "Latency runbook is not supported for the specified load balancer"
              f" type: {lb.get_load_balancer_type_name(load_balancer_type)}"),
      )
      return


class LbBackendLatencyCheck(runbook.Step):
  """Check if backend latency exceeds the threshold"""

  template = "latency::backend_latency"

  def execute(self):
    """Check backend latency for the specified forwarding rule"""
    self.forwarding_rule = lb.get_forwarding_rule(
        op.get(flags.PROJECT_ID), op.get(flags.FORWARDING_RULE_NAME),
        op.get(flags.REGION))
    project_id = op.get(flags.PROJECT_ID)
    # Define default threshold value
    threshold = op.get(flags.BACKEND_LATENCY_THRESHOLD) if op.get(
        flags.BACKEND_LATENCY_THRESHOLD) is not None else 200
    forwarding_rule = self.forwarding_rule
    forwarding_rule_name = op.get(flags.FORWARDING_RULE_NAME)
    load_balancer_type = self.forwarding_rule.load_balancer_type
    region = op.get(flags.REGION)
    op.info("Forwarding rule name: " + str(self.forwarding_rule))
    # Construct the MQL query string, incorporating filter and time range

    if load_balancer_type == lb.LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB:
      #To Do: Add support for Network Load Balancers and Pass through Load Balancers
      #To Do: Allow users to chose a specific time range

      query = f"""
          fetch http_external_regional_lb_rule
          | metric
              'loadbalancing.googleapis.com/https/external/regional/backend_latencies'
          | filter (resource.forwarding_rule_name == '{forwarding_rule_name}' && resource.region == '{region}')
          | align delta(1m)
          | every 1m
          | group_by [],
              [value_backend_latencies_average:
                mean(value.backend_latencies)]
          | within 15m
          """

    if load_balancer_type in [
        lb.LoadBalancerType.CLASSIC_APPLICATION_LB,
        lb.LoadBalancerType.GLOBAL_EXTERNAL_APPLICATION_LB,
    ]:
      query = f"""
          fetch https_lb_rule
          | metric
              'loadbalancing.googleapis.com/https/backend_latencies'
          | filter (resource.forwarding_rule_name == '{forwarding_rule_name}')
          | align delta(1m)
          | every 1m
          | group_by [],
              [value_backend_latencies_average:
                mean(value.backend_latencies)]
          | within 15m
          """

    if load_balancer_type == lb.LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB:
      query = f"""
          fetch internal_http_lb_rule
          | metric
              'loadbalancing.googleapis.com/https/internal/backend_latencies'
          | filter (resource.forwarding_rule_name == '{forwarding_rule_name}' && resource.region == '{region}')
          | align delta(1m)
          | every 1m
          | group_by [],
              [value_backend_latencies_average:
                mean(value.backend_latencies)]
          | within 15m
          """

    try:
      # Execute the query using the monitoring API
      metric = monitoring.query(project_id, query)
      values = []
      if metric:

        for _, item in metric.items(
        ):  # Iterate over the items in the metric dictionary
          if "values" in item:
            values = item["values"]

          else:
            values = [[0]]
      if values is not None:
        flattened_values = [
            float(item) for sublist in values for item in sublist
        ]
        average_latency = sum(flattened_values) / len(
            flattened_values) if flattened_values else 0
      if average_latency > threshold:
        op.add_failed(forwarding_rule,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         average_latency=round(
                                             average_latency, 2),
                                         threshold=threshold),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))

      else:
        op.add_ok(forwarding_rule,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     average_latency=round(average_latency, 2),
                                     threshold=threshold))

      return metric

    except Exception as e:
      # Catch any other errors
      op.info("An unexpected error occurred during LbBackendLatency execution.")
      op.info("Error details: " + str(e))
      raise


class LbRequestCountCheck(runbook.Step):
  """Check if request count per second exceeds the threshold"""

  def __init__(self, average_request_count=0, **kwargs):
    super().__init__(**kwargs)
    self.average_request_count = average_request_count

  template = "latency::request_count"

  def execute(self):
    """Check request count per second for the specified forwarding rule"""
    self.forwarding_rule = lb.get_forwarding_rule(
        op.get(flags.PROJECT_ID), op.get(flags.FORWARDING_RULE_NAME),
        op.get(flags.REGION))
    project_id = op.get(flags.PROJECT_ID)
    threshold = op.get(flags.REQUEST_COUNT_THRESHOLD) if op.get(
        flags.REQUEST_COUNT_THRESHOLD) is not None else 150
    forwarding_rule = self.forwarding_rule
    forwarding_rule_name = op.get(flags.FORWARDING_RULE_NAME)
    load_balancer_type = self.forwarding_rule.load_balancer_type
    region = op.get(flags.REGION)

    op.info("Forwarding rule name: " + str(self.forwarding_rule))

    # Construct the MQL query string, incorporating filter and time range

    if load_balancer_type == lb.LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB:
      query = f"""
          fetch http_external_regional_lb_rule
          | metric 'loadbalancing.googleapis.com/https/external/regional/request_count'
          | filter (resource.forwarding_rule_name == '{forwarding_rule_name}'  && resource.region == '{region}')
          | align rate(1m)
          | every 1m
          | group_by [], [value_request_count_aggregate: aggregate(value.request_count)]
          | within 15m
          """

    if load_balancer_type in [
        lb.LoadBalancerType.CLASSIC_APPLICATION_LB,
        lb.LoadBalancerType.GLOBAL_EXTERNAL_APPLICATION_LB,
    ]:
      query = f"""
          fetch https_lb_rule
          | metric 'loadbalancing.googleapis.com/https/request_count'
          | filter (resource.forwarding_rule_name == '{forwarding_rule_name}')
          | align rate(1m)
          | every 1m
          | group_by [], [value_request_count_aggregate: aggregate(value.request_count)]
          | within 15m
          """

    if load_balancer_type == lb.LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB:
      query = f"""
          fetch internal_http_lb_rule
          | metric 'loadbalancing.googleapis.com/https/internal/request_count'
          | filter (resource.forwarding_rule_name == '{forwarding_rule_name}'  && resource.region == '{region}')
          | align rate(1m)
          | every 1m
          | group_by [], [value_request_count_aggregate: aggregate(value.request_count)]
          | within 15m
          """

    try:
      # Execute the query using the monitoring API
      metric = monitoring.query(project_id, query)
      values = []
      if metric:
        for _, item in metric.items(
        ):  # Iterate over the items in the metric dictionary
          if "values" in item:
            values = item["values"]

          else:
            values = [[0]]
      if values is not None:
        flattened_values_rc = [
            float(item) for sublist in values for item in sublist
        ]
        self.average_request_count = sum(flattened_values_rc) / (
            len(flattened_values_rc) * 60) if flattened_values_rc else 0
      if self.average_request_count > threshold:
        op.add_failed(forwarding_rule,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         average_request_count=round(
                                             self.average_request_count, 2),
                                         threshold=threshold),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))

      else:
        op.add_ok(forwarding_rule,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     average_request_count=round(
                                         self.average_request_count, 2),
                                     threshold=threshold))
      return metric

    except Exception as e:
      # Catch any other errors
      op.info("An unexpected error occurred during LBRequestCount execution.")
      op.info("Error details: " + str(e))
      raise

  def get_average_request_count(self):
    """Return the calculated average_request_count to be used in the next step."""
    return self.average_request_count


class LbErrorRateCheck(runbook.Step):
  """Check if error exceeds the threshold"""

  def __init__(self, average_request_count=None, **kwargs):
    super().__init__(**kwargs)
    self.average_request_count = average_request_count

  template = "latency::error_rate"

  def execute(self):
    """Check the 5xx error rate for the specified forwarding rule"""
    self.forwarding_rule = lb.get_forwarding_rule(
        op.get(flags.PROJECT_ID), op.get(flags.FORWARDING_RULE_NAME),
        op.get(flags.REGION))
    project_id = op.get(flags.PROJECT_ID)
    threshold = op.get(flags.ERROR_RATE_THRESHOLD) if op.get(
        flags.ERROR_RATE_THRESHOLD) is not None else 1
    forwarding_rule = self.forwarding_rule
    forwarding_rule_name = op.get(flags.FORWARDING_RULE_NAME)
    load_balancer_type = self.forwarding_rule.load_balancer_type
    region = op.get(flags.REGION)

    op.info("Forwarding rule name: " + str(self.forwarding_rule))

    # Construct the MQL query string, incorporating filter and time range

    if load_balancer_type == lb.LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB:
      query = f"""
          fetch http_external_regional_lb_rule
          | metric
              'loadbalancing.googleapis.com/https/external/regional/backend_request_count'
          | filter
              (resource.forwarding_rule_name == '{forwarding_rule_name}'  && resource.region == '{region}')
              && (metric.response_code_class == 500)
          | align rate(1m)
          | every 1m
          | group_by [],
              [value_backend_request_count_aggregate:
                  aggregate(value.backend_request_count)]
          | within 15m
          """

    if load_balancer_type in [
        lb.LoadBalancerType.CLASSIC_APPLICATION_LB,
        lb.LoadBalancerType.GLOBAL_EXTERNAL_APPLICATION_LB,
    ]:
      query = f"""
          fetch https_lb_rule
          | metric
              'loadbalancing.googleapis.com/https/backend_request_count'
          | filter
              (resource.forwarding_rule_name == '{forwarding_rule_name}')
              && (metric.response_code_class == 500)
          | align rate(1m)
          | every 1m
          | group_by [],
              [value_backend_request_count_aggregate:
                  aggregate(value.backend_request_count)]
          | within 15m
          """

    if load_balancer_type == lb.LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB:
      query = f"""
          fetch internal_http_lb_rule
          | metric
              'loadbalancing.googleapis.com/https/internal/backend_request_count'
          | filter
              (resource.forwarding_rule_name == '{forwarding_rule_name}'  && resource.region == '{region}')
              && (metric.response_code_class == 500)
          | align rate(1m)
          | every 1m
          | group_by [],
              [value_backend_request_count_aggregate:
                  aggregate(value.backend_request_count)]
          | within 15m
          """

    try:

      metric = monitoring.query(project_id, query)

      values = []
      if metric and metric.get("values"):

        for _, item in metric.items(
        ):  # Iterate over the items in the metric dictionary
          if "values" in item:
            values = item["values"]
          else:
            values = [[0]]

      if values is not None:
        flattened_values_er = [
            float(item) for sublist in values for item in sublist
        ]
        average_error_count = sum(flattened_values_er) / len(
            flattened_values_er) if flattened_values_er else 0

      if average_error_count is not None and self.average_request_count is not None:
        if self.average_request_count > 0:
          average_error_rate = average_error_count / self.average_request_count * 100
        else:
          average_error_rate = 0

      if average_error_rate is None:
        average_error_rate = 0

      if average_error_rate > threshold:
        op.add_failed(forwarding_rule,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         average_error_rate=round(
                                             average_error_rate, 2),
                                         threshold=threshold),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))

      else:
        op.add_ok(forwarding_rule,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     average_error_rate=round(
                                         average_error_rate, 2),
                                     threshold=threshold))

      return metric

    except Exception as e:
      # Catch any other errors
      op.info("An unexpected error occurred during LbErrorRateCheck execution.")
      op.info("Error details: " + str(e))
      raise


class LatencyEnd(runbook.EndStep):
  """Concludes the latency diagnostics process.

  If the issue persists, it directs the user to helpful
  resources and suggests contacting support with a detailed report.
  """

  def execute(self):
    """Finalizing unhealthy backends diagnostics..."""
    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(
          kind=op.CONFIRMATION,
          message=(
              "Are you still experiencing latency issues"
              f" with your forwarding rule {op.get(flags.FORWARDING_RULE_NAME)}"
          ),
          choice_msg="Enter an option: ",
      )
      if response == op.YES:
        op.info(message=op.END_MESSAGE)
