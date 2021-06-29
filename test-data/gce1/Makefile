PROJECT_ID  := $(shell terraform output project_id | sed -e 's|"||g')
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
ZONE_1       = europe-west1-b
ZONE_2       = europe-west4-a
ZONE_EMPTY   = europe-west4-b

all:	\
	json-dumps/compute-instances-$(ZONE_1)-2.json \
	json-dumps/compute-instances-$(ZONE_1).json \
	json-dumps/compute-instances-$(ZONE_2).json \
	json-dumps/compute-instances-empty.json \
	json-dumps/compute-migs-$(ZONE_1).json \
	json-dumps/compute-migs-$(ZONE_2).json \
	json-dumps/compute-migs-empty.json \
	json-dumps/compute-zones.json \
	json-dumps/monitoring-query.json

json-dumps/compute-instances-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instances?maxResults=3' \
		| $(JSON_CLEANER) instances >$@

json-dumps/compute-instances-$(ZONE_1)-2.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instances?maxResults=3&pageToken=$(shell cat json-dumps/instances-$(ZONE_1).json | jq -r '.nextPageToken')' \
		| $(JSON_CLEANER) instances >$@

json-dumps/compute-instances-$(ZONE_2).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_2)/instances' \
		| $(JSON_CLEANER) instances >$@


json-dumps/compute-instances-empty.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_EMPTY)/instances' \
		| $(JSON_CLEANER) instances >$@

json-dumps/compute-migs-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instanceGroupManagers' \
		 >$@

json-dumps/compute-migs-$(ZONE_2).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_2)/instanceGroupManagers' \
		 >$@

json-dumps/compute-migs-empty.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_EMPTY)/instanceGroupManagers' \
		| $(JSON_CLEANER) instances >$@

json-dumps/compute-zones.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones' >$@

define MONITORING_QUERY
{ \
  "query": "fetch gce_instance::compute.googleapis.com/instance/uptime_total \
  | within 10m \
  | group_by [resource.zone, metric.instance_name] \
  | group_by 5m, [.mean, .count] \
  " \
}
endef
json-dumps/monitoring-query.json:
	$(CURL) -fsS \
		'https://monitoring.googleapis.com/v3/projects/$(PROJECT_ID)/timeSeries:query' \
		--header "Content-Type: application/json" -X POST \
		--data '$(MONITORING_QUERY)' >$@
