"""Queries related to DNS."""

from typing import Set

import dns.resolver

from gcpdiag.runbook import op


def find_dns_records(domain: str) -> Set:
  """Resolves DNS records for a given domain and returns a set of IP addresses.

  Returns an empty set if any error occurs. Logs errors using op.info.
  """
  try:
    answer = dns.resolver.resolve_name(domain)
    return set(answer.addresses())
  except dns.resolver.NoAnswer:
    op.info("Error: No records found for domain: " + domain)
    return set()
  except dns.resolver.NXDOMAIN:
    op.info("Error: Invalid domain: " + domain)
    return set()
  except dns.resolver.Timeout:
    op.info("Error: DNS resolution timed out for domain: " + domain)
    return set()
  except dns.name.EmptyLabel:
    op.info("Error: Empty A/AAAA record for domain: " + domain)
    return set()
  except dns.name.LabelTooLong:
    op.info("Error: Invalid record label too long for domain: " + domain)
    return set()
  except dns.name.NameTooLong:
    op.info("Error: DNS name too long for domain: " + domain)
    return set()
  except dns.resolver.NoNameservers:
    op.info("Error: No nameservers found for domain: " + domain)
    return set()
  except dns.exception.DNSException as e:  # Catch any other DNS exception
    op.info("Error: An unexpected DNS error occurred: " + str(e))
    return set()
