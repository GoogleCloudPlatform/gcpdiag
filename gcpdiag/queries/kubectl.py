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

# Lint as: python3
""" Queries related to Kubectl plugins. """

import functools
import logging
import os
import os.path
import subprocess
import threading

import yaml

from gcpdiag.queries import gke

config_path = os.path.expanduser('~') + '/.kube/gcpdiag-config'


class KubectlExecutor:
  """ Represents a kubectl executor. """

  lock: threading.Lock

  def __init__(self, cluster: gke.Cluster):
    self._cluster = cluster
    self.lock = threading.Lock()

  def make_kube_config(self) -> bool:
    """ Add a new kubernetes context for kubectl plugin CLIs. """

    cfg: dict = {}
    if not os.path.isfile(config_path):
      cfg['apiVersion'] = 'v1'
      cfg['users'] = [{
          'name': 'gcpdiag',
          'user': {
              'exec': {
                  'apiVersion': 'client.authentication.k8s.io/v1beta1',
                  'command': 'gke-gcloud-auth-plugin',
                  'installHint': 'x',
                  'provideClusterInfo': True,
              },
          },
      }]
      cfg['clusters'] = []
      cfg['contexts'] = []
    else:
      with open(config_path, encoding='UTF-8') as f:
        cfg = yaml.safe_load(f)

    if self._cluster.endpoint is None:
      logging.warning('No kubernetes API server endpoint found for cluster %s',
                      self._cluster.short_path)
      return False

    kubecontext = 'gcpdiag-ctx-' + self._cluster.name

    cfg['clusters'].append({
        'cluster': {
            'certificate-authority-data': self._cluster.cluster_ca_certificate,
            'server': 'https://' + self._cluster.endpoint,
        },
        'name': self._cluster.short_path,
    })
    cfg['contexts'].append({
        'context': {
            'cluster': self._cluster.short_path,
            'user': 'gcpdiag',
        },
        'name': kubecontext,
    })

    self._kubecontext = kubecontext

    config_text = yaml.dump(cfg, default_flow_style=False)
    with open(config_path, 'w', encoding='UTF-8') as config_file:
      config_file.write(config_text)

    return True

  def verify_auth(self) -> bool:
    """ Verify the authentication for kubernetes by running kubeclt cluster-info.

    Will raise a warning and return False if authenticaiton failed.
    """
    _, stderr = self.kubectl_execute([
        'kubectl', 'cluster-info', '--kubeconfig', config_path, '--context',
        self._kubecontext
    ])
    if stderr:
      logging.warning('Failed to authenticate kubectl for cluster %s: %s',
                      self._cluster.short_path, stderr.strip('\n'))
      return False
    return True

  def kubectl_execute(self, command_list: list[str]):
    """ Execute a kubectl command.

      Will take a list of strings which contains all the command and parameters to be executed
      and return the stdout and stderr of the execution.
    """
    res = subprocess.run(command_list,
                         check=False,
                         capture_output=True,
                         text=True)
    return res.stdout, res.stderr


@functools.lru_cache()
def get_kubectl_executor(c: gke.Cluster):
  """ Create a kubectl_executor for a GKE cluster. """
  executor = KubectlExecutor(cluster=c)
  with executor.lock:
    if not executor.make_kube_config():
      return None
  if not executor.verify_auth():
    return None
  return executor


def clean_up():
  """ Delete the kubeconfig file generated for gcpdiag. """
  os.remove(config_path)
