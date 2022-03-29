# Copyright 2021 Google LLC
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

# Lint as: python3
"""Utilities functions to make writing GKE lint rules easier."""

import collections
import logging
from typing import Any, Callable, Dict, Set, Tuple

from gcpdiag import models
from gcpdiag.queries import gce, gke, logs


class _CantMapLogEntry(BaseException):
  pass


# We also use context as index just to be sure, in case one day we have
# situations where this code is running multiple times with different context
# objects.
_clusters_by_name: Dict[models.Context, Dict[Tuple[str, str, str],
                                             gke.Cluster]] = {}
_clusters_by_instance_id: Dict[models.Context, Dict[str, Tuple[gke.Cluster,
                                                               str]]] = {}


def _initialize_clusters_by_name(context: models.Context):
  if not context in _clusters_by_name:
    _clusters_by_name[context] = {}
    clusters = gke.get_clusters(context)
    for c in clusters.values():
      _clusters_by_name[context][(c.project_id, c.location, c.name)] = c


def _initialize_clusters_by_instance_id(context: models.Context):
  # Don't assume that _initialize_clusters_by_name is called first,
  # so make sure here, even though actually it was already called.
  _initialize_clusters_by_name(context)
  if not context in _clusters_by_instance_id:
    _clusters_by_instance_id[context] = {}
    for instance_id, instance in gce.get_instances(context).items():
      try:
        c = _clusters_by_name[context][(
            instance.project_id,
            instance.get_metadata('cluster-location'),
            instance.get_metadata('cluster-name'),
        )]
        # Also store the instance name because that's not available in the
        # logs sometimes.
        _clusters_by_instance_id[context][instance_id] = (c, instance.name)
      except KeyError:
        # Filter out non-GKE nodes.
        continue


def _gke_node_of_log_entry(context, log_entry):
  try:
    labels = log_entry['resource']['labels']
    project_id = labels['project_id']
  except KeyError:
    logging.warning('log entry without project_id label: %s', log_entry)
    raise _CantMapLogEntry() from KeyError

  if 'node_name' in labels:
    # GKE node log
    try:
      c = _clusters_by_name[context][(project_id, labels['location'],
                                      labels['cluster_name'])]
      return (c, labels['node_name'])
    except KeyError as err:
      # log entry for a node that wasn't selected by context
      raise _CantMapLogEntry() from err
  elif 'instance_id' in labels:
    # GCE instance log
    # Note that once the instance is deleted, we can't determine anymore to what
    # cluster a GCE instance belonged. I wish we had GKE node labels in GCE
    # instance logs of GKE nodes...
    try:
      return _clusters_by_instance_id[context][labels['instance_id']]
    except KeyError as err:
      raise _CantMapLogEntry from err
  else:
    raise _CantMapLogEntry()


def _gke_cluster_of_log_entry(context, log_entry):

  try:
    labels = log_entry['resource']['labels']
    project_id = labels['project_id']
  except KeyError:
    logging.warning('log entry without project_id label: %s', log_entry)
    raise _CantMapLogEntry() from KeyError

  try:
    c = _clusters_by_name[context][(project_id, labels['location'],
                                    labels['cluster_name'])]
    return c
  except KeyError as err:
    raise _CantMapLogEntry() from err


def gke_logs_find_bad_nodes(context: models.Context,
                            logs_by_project: Dict[str, logs.LogsQuery],
                            filter_f: Callable) -> Dict[gke.Cluster, Set[str]]:
  """Go through logs and find GKE node-level issues.

  Returns dict with clusters as key and node list of "bad nodes" as
  value."""
  _initialize_clusters_by_name(context)
  _initialize_clusters_by_instance_id(context)

  # Process the log entries.
  bad_nodes_by_cluster = collections.defaultdict(set)
  for query in logs_by_project.values():
    for log_entry in query.entries:
      # Retrieved logs are not guaranteed to only contain what we defined as
      # "filter_str", so we need to filter out what isn't ours.
      if not filter_f(log_entry):
        continue

      try:
        (c, node_name) = _gke_node_of_log_entry(context, log_entry)
        bad_nodes_by_cluster[c].add(node_name)
      except _CantMapLogEntry:
        continue
  return bad_nodes_by_cluster


def gke_logs_find_bad_clusters(context: models.Context,
                               logs_by_project: Dict[str, logs.LogsQuery],
                               filter_f: Callable) -> Dict[gke.Cluster, Any]:
  """Go through logs and find GKE cluster-level issues.

  Returns dict with clusters as key and first matched log entry as
  value."""

  _initialize_clusters_by_name(context)

  # Process the log entries.
  bad_clusters = {}
  for query in logs_by_project.values():
    for log_entry in query.entries:
      # Retrieved logs are not guaranteed to only contain what we defined as
      # "filter_str", so we need to filter out what isn't ours.
      if not filter_f(log_entry):
        continue

      try:
        c = _gke_cluster_of_log_entry(context, log_entry)
        if c in bad_clusters:
          # only store the first log message
          continue
        bad_clusters[c] = log_entry
      except _CantMapLogEntry:
        continue
  return bad_clusters
