# Copyright 2024 Google LLC
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
"""Queries related to DNS."""

import logging
from typing import Set

import dns.resolver


def find_dns_records(domain: str) -> Set:
  """Resolves DNS records for a given domain and returns a set of IP addresses.

  Returns an empty set if any error occurs. Logs errors using logging.info.
  """
  try:
    answer = dns.resolver.resolve_name(domain)
    return set(answer.addresses())
  except dns.resolver.NoAnswer:
    logging.info("Error: No records found for domain: %s", domain)
    return set()
  except dns.resolver.NXDOMAIN:
    logging.info("Error: Invalid domain: %s", domain)
    return set()
  except dns.resolver.Timeout:
    logging.info("Error: DNS resolution timed out for domain: %s", domain)
    return set()
  except dns.name.EmptyLabel:
    logging.info("Error: Empty A/AAAA record for domain: %s", domain)
    return set()
  except dns.name.LabelTooLong:
    logging.info("Error: Invalid record label too long for domain: %s", domain)
    return set()
  except dns.name.NameTooLong:
    logging.info("Error: DNS name too long for domain: %s", domain)
    return set()
  except dns.resolver.NoNameservers:
    logging.info("Error: No nameservers found for domain: %s", domain)
    return set()
  except dns.exception.DNSException as e:  # Catch any other DNS exception
    logging.info("Error: An unexpected DNS error occurred: %s", str(e))
    return set()
