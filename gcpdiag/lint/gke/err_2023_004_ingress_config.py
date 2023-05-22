# Copyright 2023 Google LLC
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
"""GKE ingresses are well configured.

Verify that the Google Kubernetes Engine ingresses are well configured.
This rule will run a command line tool check-gke-ingress to inspect the ingresses.
"""

import json
import logging

from gcpdiag import lint, models
from gcpdiag.queries import gke, kubectl

executor_dict = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  for _, c in sorted(clusters.items()):
    executor = kubectl.get_kubectl_executor(c)
    if executor is None:
      continue
    executor_dict[c] = executor


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return
  for _, c in sorted(clusters.items()):
    if c not in executor_dict:
      report.add_skipped(c, 'failed to access k8s cluster')
      continue
    try:
      stdout, stderr = kubectl.check_gke_ingress(executor_dict[c])
    except FileNotFoundError as err:
      logging.warning('Can not inspect Kubernetes resources: %s: %s',
                      type(err).__name__, err)
      report.add_skipped(c, 'failed to access k8s cluster')
      continue

    if stderr:
      report.add_skipped(c,
                         'failed to run kubectl check-gke-ingress: ' + stderr)
      continue
    result = json.loads(stdout)

    failed = False
    message = ''
    for resource in result['resources']:
      for check in resource['checks']:
        if check['result'] == 'FAILED':
          failed = True
          message += kubectl.error_message(check['name'], resource['kind'],
                                           resource['namespace'],
                                           resource['name'], check['message'])
    if not failed:
      report.add_ok(c)
    else:
      report.add_failed(c, message[:-1])
