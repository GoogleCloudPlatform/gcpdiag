# Lint as: python3
"""List and describe GCE instances."""

from gcp_doctor.inspect.apis import get_api


def get_instances(context):
  compute = get_api('compute', 'v1')
  result = compute.instances().list(
      project=context['project'], zone=context['zone']).execute()
  if 'kind' not in result or result[
      'kind'] != 'compute#instanceList' or 'items' not in result:
    raise RuntimeError('unexpected result from compute.instances().list')
  return result['items']

# class ComputeInstances:
#   def __init__(self, context):
#     self._instances = _get_instances(context)
#
#   def __iter__(self):
#     return self._instances.__iter__()
