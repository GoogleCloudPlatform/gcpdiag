PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
ZONE_1       = europe-west1-b
ZONE_2       = europe-west4-a

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340001
FAKE_ORG_ID = 11112222

COMPUTE_INSTANCES_MAXRESULTS=3

all:	\
	json-dumps/compute-effective-firewalls-default.json \
	json-dumps/compute-igs-$(ZONE_1).json \
	json-dumps/compute-igs-$(ZONE_2).json \
	json-dumps/compute-igs-empty.json \
	json-dumps/compute-instances-$(ZONE_1).json \
	json-dumps/compute-instances-$(ZONE_1)-2.json \
	json-dumps/compute-instances-$(ZONE_2).json \
	json-dumps/compute-instances-$(ZONE_2)-2.json \
	json-dumps/compute-instances-empty.json \
	json-dumps/compute-migs-$(ZONE_1).json \
	json-dumps/compute-migs-$(ZONE_2).json \
	json-dumps/compute-migs-empty.json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-project.json \
	json-dumps/compute-regions.json \
	json-dumps/compute-templates.json \
	json-dumps/compute-zones.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/monitoring-query.json \
	json-dumps/project.json \
	json-dumps/services.json

include ../Makefile.inc

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
		--data '$(MONITORING_QUERY)' \
		| $(SED_SUBST_FAKE) >$@
