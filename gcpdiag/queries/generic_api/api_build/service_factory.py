"""Helper functions to create service objects for the API."""

from gcpdiag.queries.generic_api.api_build import api


def build_api(service_name: str, api_base_url: str, creds: api.Creds,
              retry_strategy: api.RetryStrategy) -> object:
  """Builds a service object for the given service name."""
  # Avoid circular import dependencies by importing the required modules here.
  # pylint: disable=import-outside-toplevel
  if service_name == "datafusion":
    from gcpdiag.queries.generic_api.datafusion import datafusion

    return datafusion.Datafusion(api_base_url,
                                 creds=creds,
                                 retry_strategy=retry_strategy)
  else:
    raise ValueError(f"Unknown service name: {service_name}")
