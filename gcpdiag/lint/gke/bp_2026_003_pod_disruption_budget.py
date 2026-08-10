# Copyright 2026 Google LLC
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
"""GKE workloads have Pod Disruption Budgets (PDBs) configured.

Check that there are no active recommendations from Active Assist for missing
or misconfigured Pod Disruption Budgets (PDBs).
"""

import logging
import re

from gcpdiag import lint, models, utils
from gcpdiag.queries import gke, recommender

VALID_PDB_SUBTYPES = {
  'PDB_UNPROTECTED_STATEFULSET',
  'PDB_UNPERMISSIVE',
  'PDB_STATEFULSET_WITHOUT_PROBES',
  'DEPLOYMENT_MISSING_PDB',
  'GKE_WORKLOAD_PDB_MISSING',
}


def prepare_rule(context: models.Context) -> None:
  gke.get_clusters(context)


def prefetch_rule(context: models.Context) -> None:
  clusters = gke.get_clusters(context)
  if not clusters:
    return

  # Find all unique locations of GKE clusters
  locations = {c.location for c in clusters.values()}

  # Prefetch recommendations for each unique location
  for loc in locations:
    try:
      recommender.get_recommendations(
        context, 'google.container.DiagnosisRecommender', location=loc
      )
    except utils.GcpApiError as e:
      logging.debug('failed to prefetch recommendations for location %s: %s', loc, e)


def format_recommendation(rec) -> str:
  subtype = rec.recommender_subtype
  overview = rec.content.get('overview', {})

  # 1. PDB_UNPROTECTED_STATEFULSET
  if subtype == 'PDB_UNPROTECTED_STATEFULSET':
    recs = overview.get('podDisruptionRecommendation', [])
    details = []
    for r in recs:
      ss_info = r.get('statefulSetInfo', {})
      ss_name = ss_info.get('statefulSetName')
      ss_ns = ss_info.get('statefulSetNamespace')
      if ss_name and ss_ns:
        details.append(f'StatefulSet {ss_ns}/{ss_name}')
    if details:
      return f'StatefulSet(s) missing Pod Disruption Budget: {", ".join(details)}'
    return 'StatefulSet is missing a matching Pod Disruption Budget'

  # 2. PDB_UNPERMISSIVE
  elif subtype == 'PDB_UNPERMISSIVE':
    recs = overview.get('podDisruptionRecommendation', [])
    details = []
    for r in recs:
      pdb_info = r.get('pdbInfo', {})
      pdb_name = pdb_info.get('pdbName') or pdb_info.get('name')
      pdb_ns = pdb_info.get('pdbNamespace') or pdb_info.get('namespace')
      if pdb_name and pdb_ns:
        details.append(f'PDB {pdb_ns}/{pdb_name}')
    if details:
      return f'Pod Disruption Budget(s) do not allow voluntary disruptions: {", ".join(details)}'
    return 'Pod Disruption Budget does not allow any voluntary disruptions'

  # 3. PDB_STATEFULSET_WITHOUT_PROBES
  elif subtype == 'PDB_STATEFULSET_WITHOUT_PROBES':
    recs = overview.get('podDisruptionRecommendation', [])
    details = []
    for r in recs:
      ss_info = r.get('statefulSetInfo', {})
      ss_name = ss_info.get('statefulSetName')
      ss_ns = ss_info.get('statefulSetNamespace')
      if ss_name and ss_ns:
        details.append(f'StatefulSet {ss_ns}/{ss_name}')
    if details:
      return f'StatefulSet(s) covered by PDB missing readiness probes: {", ".join(details)}'
    return 'StatefulSet configured with a PDB is missing readiness probes'

  # 4. DEPLOYMENT_MISSING_PDB or GKE_WORKLOAD_PDB_MISSING
  elif subtype in ['DEPLOYMENT_MISSING_PDB', 'GKE_WORKLOAD_PDB_MISSING']:
    recs = overview.get('podDisruptionRecommendation', [])
    details = []
    for r in recs:
      dep_info = r.get('deploymentInfo', {})
      dep_name = dep_info.get('deploymentName') or dep_info.get('name')
      dep_ns = dep_info.get('deploymentNamespace') or dep_info.get('namespace')
      if dep_name and dep_ns:
        details.append(f'Deployment {dep_ns}/{dep_name}')
    if details:
      return f'Deployment(s) missing Pod Disruption Budget: {", ".join(details)}'

    # Fallback to parsing from raw description if it matches standard format
    m = re.search(
      r'Workload missing Pod Disruption Budget:\s*(.*?)\s*'
      r'in namespace\s*(\S+)',
      rec.description,
    )
    if m:
      return f'Workload missing Pod Disruption Budget: {m.group(2)}/{m.group(1)}'

    return 'Deployment is missing a matching Pod Disruption Budget'

  # Fallback: clean the raw description
  desc = rec.description
  desc = re.sub(r'\[.*?\]\(http.*?\)', '', desc)
  desc = desc.strip().rstrip('.')
  desc = desc.replace('’', "'").replace('‘', "'")
  return desc


def run_rule(context: models.Context, report: lint.LintReportRuleInterface) -> None:
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  for _, c in sorted(clusters.items()):
    # Fetch recommendations specifically for this cluster's location
    try:
      recommendations = recommender.get_recommendations(
        context, 'google.container.DiagnosisRecommender', location=c.location
      )
    except utils.GcpApiError as e:
      logging.debug(
        'failed to fetch recommendations for cluster %s in %s: %s',
        c.name,
        c.location,
        e,
      )
      recommendations = []

    # Find matching recommendations for the cluster
    pdb_recs = []
    for rec in recommendations:
      # Check if this recommendation targets the current cluster
      is_match = False
      for res in rec.target_resources:
        if res.endswith(f'locations/{c.location}/clusters/{c.name}') or res.endswith(
          f'zones/{c.location}/clusters/{c.name}'
        ):
          is_match = True
          break
      if not is_match:
        continue

      # Check if the recommendation is about PDB
      if rec.recommender_subtype in VALID_PDB_SUBTYPES:
        pdb_recs.append(rec)

    if pdb_recs:
      if len(pdb_recs) == 1:
        reasons_str = format_recommendation(pdb_recs[0])
      else:
        reasons_str = '\n' + '\n'.join([f'- {format_recommendation(rec)}' for rec in pdb_recs])
      report.add_failed(
        c,
        f'workloads missing or misconfigured Pod Disruption Budgets: {reasons_str}',
      )
    else:
      report.add_ok(c)
