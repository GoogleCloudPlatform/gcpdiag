"""Queries related to DNS."""

from typing import Set

domain_to_ips = {
    'natka123.com': {'1.2.3.4', '1.2.3.5'},
    'second.natka123.com': {'2600:1901:0:d0d7::'},
    'test.natka123.com': {'192.168.3.4'},
    'test.org': {'192.168.3.5'},
    'second.test.org': {'2600:1901:0:d0d7::'},
}


def find_dns_records(domain: str) -> Set:
  return domain_to_ips[domain]
