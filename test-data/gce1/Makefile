PROJECT_ID  := $(shell terraform output project_id | sed -e 's|"||g')
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
ZONE_1       = europe-west1-b
ZONE_2       = europe-west4-a
ZONE_EMPTY   = europe-west4-b

all:	json-dumps/zones.json \
	json-dumps/instances-$(ZONE_1).json \
	json-dumps/instances-$(ZONE_2).json \
	json-dumps/instances-empty.json

json-dumps/zones.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones' >$@

json-dumps/instances-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instances' \
		| $(JSON_CLEANER) instances >$@

json-dumps/instances-$(ZONE_2).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_2)/instances' \
		| $(JSON_CLEANER) instances >$@

json-dumps/instances-empty.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_EMPTY)/instances' \
		| $(JSON_CLEANER) instances >$@
