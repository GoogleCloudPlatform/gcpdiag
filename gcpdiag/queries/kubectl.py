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
import subprocess
import threading

import yaml

from gcpdiag import config
from gcpdiag.queries import gke


def get_config_path():
  return config.get_cache_dir() + '/gcpdiag-config'


class KubectlExecutor:
  """Represents a kubectl executor."""

  lock: threading.Lock

  def __init__(self, cluster: gke.Cluster):
    self.cluster = cluster
    self.lock = threading.Lock()

  def make_kube_config(self) -> bool:
    """Add a new kubernetes context for kubectl plugin CLIs."""

    cfg: dict = {}
    if not os.path.isfile(get_config_path()):
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
      with open(get_config_path(), encoding='UTF-8') as f:
        cfg = yaml.safe_load(f)

    if self.cluster.endpoint is None:
      logging.warning('No kubernetes API server endpoint found for cluster %s',
                      self.cluster.short_path)
      return False

    kubecontext = 'gcpdiag-ctx-' + self.cluster.name

    cfg['clusters'].append({
        'cluster': {
            'certificate-authority-data': self.cluster.cluster_ca_certificate,
            'server': 'https://' + self.cluster.endpoint,
        },
        'name': self.cluster.short_path,
    })
    cfg['contexts'].append({
        'context': {
            'cluster': self.cluster.short_path,
            'user': 'gcpdiag',
        },
        'name': kubecontext,
    })

    self.kubecontext = kubecontext

    config_text = yaml.dump(cfg, default_flow_style=False)
    # Create/overwrite the config file with strict permissions (0600)
    config_path = get_config_path()
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='UTF-8') as config_file:
      config_file.write(config_text)
    # Ensure permissions are restricted even if the file already existed
    os.chmod(config_path, 0o600)

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


def verify_auth(executor: KubectlExecutor) -> bool:
  """ Verify the authentication for kubernetes by running kubeclt cluster-info.

  Will raise a warning and return False if authentication failed.
  """
  _, stderr = executor.kubectl_execute([
      'kubectl', 'cluster-info', '--kubeconfig',
      get_config_path(), '--context', executor.kubecontext
  ])
  if stderr:
    logging.warning('Failed to authenticate kubectl for cluster %s: %s',
                    executor.cluster.short_path, stderr.strip('\n'))
    return False
  return True


def check_gke_ingress(executor: KubectlExecutor):
  return executor.kubectl_execute([
      'kubectl', 'check-gke-ingress', '--kubeconfig',
      get_config_path(), '--context', executor.kubecontext
  ])


@functools.lru_cache()
def get_kubectl_executor(c: gke.Cluster):
  """ Create a kubectl_executor for a GKE cluster. """
  executor = KubectlExecutor(cluster=c)
  with executor.lock:
    if not executor.make_kube_config():
      return None
  try:
    if not verify_auth(executor):
      logging.warning('Authentication failed for cluster %s', c.short_path)
      return None
  except FileNotFoundError as err:
    logging.warning('Can not inspect Kubernetes resources: %s: %s',
                    type(err).__name__, err)
    return None
  return executor


def clean_up():
  """ Delete the kubeconfig file generated for gcpdiag. """
  try:
    os.remove(get_config_path())
  except OSError as err:
    logging.debug('Error cleaning up kubeconfig file used by gcpdiag: %s: %s',
                  type(err).__name__, err)


def error_message(rule_name, kind, namespace, name, message) -> str:
  return f'Check rule {rule_name} on {kind} {namespace}/{name} failed: {message}\n'
