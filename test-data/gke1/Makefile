PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
GKE2_SA     := $(shell terraform output -raw gke2_sa)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = europe-west4
ZONE_1       = europe-west4-a
ZONE_EMPTY   = europe-west1-b
SUBNETWORK_1 = gke1-subnet

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340002
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/compute-effective-firewalls-default.json \
	json-dumps/compute-instances-$(ZONE_1).json \
	json-dumps/compute-instances-empty.json \
	json-dumps/compute-migs-$(ZONE_1).json \
	json-dumps/compute-migs-empty.json \
	json-dumps/compute-igs-empty.json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-project.json \
	json-dumps/compute-subnetworks-europe-west4.json \
	json-dumps/compute-subnetwork-policy.json \
	json-dumps/compute-templates.json \
	json-dumps/compute-regions.json \
	json-dumps/compute-zones.json \
	json-dumps/compute-routers-europe-west4.json \
	json-dumps/container-clusters.json \
	json-dumps/container-server-config-$(REGION_1).json \
	json-dumps/container-server-config-$(ZONE_1).json \
	json-dumps/iam-policy.json \
	json-dumps/iam-roles-custom.json \
	json-dumps/iam-roles-predefined-1.json.gz \
	json-dumps/iam-roles-predefined-2.json.gz \
	json-dumps/iam-roles-get.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/iam-service-account-policy.json \
	json-dumps/logging-entries-1.json \
	json-dumps/project.json \
	json-dumps/services.json

# compute.googleapis.com

json-dumps/compute-regions.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-zones.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instances' \
		| $(JSON_CLEANER) instances \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-migs-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instanceGroupManagers' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-empty.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_EMPTY)/instances' \
		| $(JSON_CLEANER) instances \
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

json-dumps/compute-project.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)' \
		| $(JSON_CLEANER) compute-project \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-network-default.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/networks/default' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-effective-firewalls-default.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/networks/default/getEffectiveFirewalls' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-templates.json:
	ZONE=$(subst json-dumps/,,$%); \
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/instanceTemplates' \
		| $(JSON_CLEANER) compute-templates \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-subnetworks-%.json:
	REGION=$(subst json-dumps/,,$*); \
	$(CURL) -fsS \
	        "https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$$REGION/subnetworks" \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-subnetwork-policy.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$(REGION_1)/subnetworks/$(SUBNETWORK_1)/getIamPolicy' \
		--header "Content-Type:text/json" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-routers-%.json:
	REGION=$(subst json-dumps/,,$*); \
	$(CURL) -fsS \
	        "https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$$REGION/routers" \
		| $(SED_SUBST_FAKE) >$@

# cloudresourcemanager.googleapis.com

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-policy.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID):getIamPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

# iam.googleapis.com

json-dumps/iam-roles-predefined-1.json.gz:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/roles?view=FULL&pageSize=500' \
		| $(SED_SUBST_FAKE) \
	        | gzip -c >$@

json-dumps/iam-roles-predefined-2.json.gz: json-dumps/iam-roles-predefined-1.json.gz
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/roles?view=FULL&pageSize=500&pageToken=$(shell zcat json-dumps/iam-roles-predefined-1.json.gz | jq -r '.nextPageToken')' \
		| $(SED_SUBST_FAKE) \
	        | gzip -c >$@

json-dumps/iam-roles-custom.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/roles?view=FULL&pageSize=500' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-roles-get.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/roles/container.nodeServiceAgent' \
		| $(SED_SUBST_FAKE) \
		| jq '{"roles": [.]}' >$@

json-dumps/iam-service-accounts.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/serviceAccounts' \
		| $(JSON_CLEANER) service-accounts \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-service-account-policy.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/$(GKE2_SA):getIamPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

# container.googleapis.com

json-dumps/container-clusters.json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/locations/-/clusters' \
		| $(JSON_CLEANER) clusters \
		| $(SED_SUBST_FAKE) >$@

json-dumps/container-server-config-$(REGION_1).json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_1)/serverConfig' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/container-server-config-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/serverconfig' \
		| $(SED_SUBST_FAKE) >$@

# serviceusage.googleapis.com

json-dumps/services.json:
	$(CURL) -fsS \
	        'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
		| $(SED_SUBST_FAKE) >$@


# If you need to recreate the JSON: adapt the timestamp and make sure that there are some entries found.
define LOGGING_ENTRIES_BODY
{
	"resourceNames": ["projects/$(PROJECT_ID)"],
	"orderBy": "timestamp desc",
	"filter": "
		timestamp > \"2021-11-24T00:00:00+00:00\" AND
		timestamp < \"2021-11-25T00:00:00+00:00\" AND
		resource.type=\"gce_instance_group_manager\" AND
		operation.last=\"true\" AND
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
