PROJECT_ID  := $(shell terraform output project_id)
PROJECT_ID_SUFFIX := $(shell terraform output project_id_suffix)
PROJECT_NR  := $(shell terraform output project_nr)
ORG_ID      := $(shell terraform output org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = us-central1
REGION       = europe-west4
ZONE         = us-central1-a
ZONE_1         = us-central1-b
ZONE_2         = us-central1-c
ZONE_3         = us-central1-f

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340005
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
  json-dumps/project.json \
	json-dumps/compute-regions.json \
	json-dumps/dataproc-clusters-$(REGION_1).json \
	json-dumps/services.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/iam-policy.json \
	json-dumps/compute-instances-$(ZONE).json \
	json-dumps/compute-instances-$(ZONE_1).json \
	json-dumps/compute-instances-$(ZONE_2).json \
	json-dumps/compute-instances-$(ZONE_3).json \
	json-dumps/compute-subnetworks-aggregated.json \
	json-dumps/logging-entries-1.json \
	json-dumps/compute-network-test-bad-network.json \

include ../Makefile.inc

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-regions.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/dataproc-clusters-$(REGION_1).json:
	$(CURL) -fsS \
	  'https://dataproc.googleapis.com/v1/projects/$(PROJECT_ID)/regions/$(REGION_1)/clusters' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fsS \
	  'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/iam-service-accounts.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/serviceAccounts' \
		| $(JSON_CLEANER) service-accounts \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-policy.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID):getIamPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

# If you need to recreate the JSON: adapt the timestamp and make sure that there are some entries found.
define LOGGING_ENTRIES_BODY
{
	"resourceNames": ["projects/$(PROJECT_ID)"],
	"orderBy": "timestamp desc",
	"filter": "
		timestamp > \"2024-06-24T00:00:00+00:00\" AND
		timestamp < \"2024-06-26T00:00:00+00:00\" AND
		resource.type=\"cloud_dataproc_cluster\" AND
		log_id(\"cloudaudit.googleapis.com%2Factivity\")
	"
}
endef
export LOGGING_ENTRIES_BODY

json-dumps/logging-entries-1.json:
	$(CURL) -fsS \
		'https://logging.googleapis.com/v2/entries:list' \
		--header "Content-Type:text/json" \
		-d "$$LOGGING_ENTRIES_BODY" \
		| $(SED_SUBST_FAKE) >$@
