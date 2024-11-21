"""
Returns project-wide product list
"""
from typing import Dict


def get_product_list() -> Dict:

  return {
      'apigee':
          '[Apigee API Management](https://cloud.google.com/apigee)',
      'asm':
          '[Anthos Service Mesh](https://cloud.google.com/anthos)',
      'bigquery':
          '[BigQuery](https://cloud.google.com/bigquery)',
      'billing':
          '[Cloud Billing](https://cloud.google.com/billing)',
      'cloudrun':
          '[Cloud Run](https://cloud.google.com/run)',
      'cloudsql':
          '[CloudSQL](https://cloud.google.com/sql)',
      'composer':
          '[Cloud Composer](https://cloud.google.com/composer)',
      'dataflow':
          '[Dataflow](https://cloud.google.com/dataflow)',
      'datafusion':
          '[Cloud Data Fusion](https://cloud.google.com/data-fusion)',
      'dataproc':
          '[Cloud Dataproc](https://cloud.google.com/dataproc)',
      'gae':
          '[App Engine](https://cloud.google.com/appengine)',
      'gcb':
          '[Cloud Build](https://cloud.google.com/build)',
      'gce':
          '[Compute Engine](https://cloud.google.com/compute)',
      'gcf':
          '[Cloud Functions](https://cloud.google.com/functions)',
      'gcs':
          '[Cloud Storage](https://cloud.google.com/storage)',
      'gke':
          '[Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)',
      'iam':
          '[Identity and Access Management (IAM)](https://cloud.google.com/iam)',
      'interconnect':
          '[Interconnect](https://cloud.google.com/network-connectivity/docs/interconnect)',
      'lb':
          '[Load balancing](https://cloud.google.com/load-balancing)',
      'monitoring':
          'https://cloud.google.com/monitoring',
      'notebooks':
          '[Vertex AI Workbench](https://cloud.google.com/vertex-ai-workbench)',
      'nat':
          '[Cloud NAT](https://cloud.google.com/nat)',
      'pubsub':
          '[Cloud Pub/Sub](https://cloud.google.com/pubsub/)',
      'tpu':
          '[Cloud TPU](https://cloud.google.com/tpu)',
      'vertex':
          '[Vertex AI](https://cloud.google.com/vertex-ai)',
      'vpc':
          '[Virtual Private Cloud](https://cloud.google.com/vpc)'
  }
