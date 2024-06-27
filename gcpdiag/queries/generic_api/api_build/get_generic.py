""" Helper method to initialize API object """
from gcpdiag import caching, config
from gcpdiag.async_queries.api import (default_random,
                                       exponential_random_retry_strategy,
                                       gcpdiag_creds)
from gcpdiag.queries.generic_api.api_build import api, service_factory


def pick_creds_implementation() -> api.Creds:
  try:
    # This is for Google-internal use only and allows us to modify the request
    # to make it work also internally. The import will fail for the public
    # version of gcpdiag.
    # pylint: disable=import-outside-toplevel
    from gcpdiag_google_internal import async_api_creds_internal

    return async_api_creds_internal.GcpdiagInternalCreds()
  except ImportError:
    return gcpdiag_creds.GcpdiagCreds()


@caching.cached_api_call(in_memory=True)
def get_generic_api(service_name: str, api_base_url: str) -> api.API:
  """Args:

    api_base_url:
    version:

  Returns:
  """

  return service_factory.build_api(
      service_name,
      api_base_url,
      creds=pick_creds_implementation(),
      retry_strategy=exponential_random_retry_strategy.
      ExponentialRandomTimeoutRetryStrategy(
          retries=config.API_RETRIES,
          random_pct=config.API_RETRY_SLEEP_RANDOMNESS_PCT,
          multiplier=config.API_RETRY_SLEEP_MULTIPLIER,
          random=default_random.Random(),
      ),
  )
