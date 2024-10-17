"""Updates IP addresses of global forwarding rules for consistent test mocks.

Replaces dynamically assigned IP addresses from API responses with fixed IPs
to ensure predictable output for testing.  New projects provisioned with
different IPs will have their forwarding rule IPs rewritten to these constants.
"""

import json
import sys

new_global_ip_addresses = {
    'https-content-rule': ('1.2.3.4'),
    'https-content-rule-working': ('2600:1901:0:d0d7::'),
    'ssl-rule': ('192.168.3.5')
}

data = json.load(sys.stdin)

if ('items' in data and 'global' in data['items'] and
    'forwardingRules' in data['items']['global']):
  for rule in data['items']['global']['forwardingRules']:
    if rule['name'] in new_global_ip_addresses:
      rule['IPAddress'] = new_global_ip_addresses[rule['name']]

print(json.dumps(data, indent=2))
