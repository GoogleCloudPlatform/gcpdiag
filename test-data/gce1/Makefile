PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
ZONE_1       = europe-west1-b
ZONE_2       = europe-west4-a
ZONE_EMPTY   = europe-west4-b

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340001
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/compute-effective-firewalls-default.json \
	json-dumps/compute-instances-$(ZONE_1)-2.json \
	json-dumps/compute-instances-$(ZONE_1).json \
	json-dumps/compute-instances-$(ZONE_2).json \
	json-dumps/compute-instances-empty.json \
	json-dumps/compute-migs-$(ZONE_1).json \
	json-dumps/compute-migs-$(ZONE_2).json \
	json-dumps/compute-igs-$(ZONE_2).json \
	json-dumps/compute-templates.json \
	json-dumps/compute-migs-empty.json \
	json-dumps/compute-igs-empty.json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-project.json \
	json-dumps/compute-regions.json \
	json-dumps/compute-zones.json \
	json-dumps/monitoring-query.json \
	json-dumps/iam-policy.json \
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/iam-service-accounts.json

json-dumps/compute-effective-firewalls-default.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/networks/default/getEffectiveFirewalls' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instances?maxResults=3' \
		| $(JSON_CLEANER) instances \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-$(ZONE_1)-2.json: json-dumps/compute-instances-$(ZONE_1).json
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instances?maxResults=3&pageToken=$(shell cat json-dumps/compute-instances-$(ZONE_1).json | jq -r '.nextPageToken')' \
		| $(JSON_CLEANER) instances \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-$(ZONE_2).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_2)/instances' \
		| $(JSON_CLEANER) instances \
		| $(SED_SUBST_FAKE) >$@


json-dumps/compute-instances-empty.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_EMPTY)/instances' \
		| $(JSON_CLEANER) instances \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-migs-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instanceGroupManagers' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-migs-$(ZONE_2).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_2)/instanceGroupManagers' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-igs-$(ZONE_2).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_2)/instanceGroups' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-templates.json:
	ZONE=$(subst json-dumps/,,$%); \
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/instanceTemplates' \
		| $(JSON_CLEANER) compute-templates \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-migs-empty.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_EMPTY)/instanceGroupManagers' \
		| $(JSON_CLEANER) instances \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-igs-empty.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_EMPTY)/instanceGroups' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-network-default.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/networks/default' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-project.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)' \
		| $(JSON_CLEANER) compute-project \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-regions.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-zones.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-policy.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID):getIamPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fv \
	        'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
		| $(SED_SUBST_FAKE) >$@

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

json-dumps/iam-service-accounts.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/serviceAccounts' \
		| $(JSON_CLEANER) service-accounts \
		| $(SED_SUBST_FAKE) >$@
