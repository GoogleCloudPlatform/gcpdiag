PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = us-central1
ZONE_1       = us-central1-b
ZONE_2       = us-central1-a

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340010
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \


all:	\
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/datafusion-instances.json \
	json-dumps/iam-policy.json \
        json-dumps/iam-service-accounts.json \
        json-dumps/iam-service-account-policy.json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-subnetworks-europe-west4.json \
	json-dumps/compute-subnetworks-us-central1.json \
	json-dumps/compute-effective-firewalls-default.json \
	json-dumps/compute-subnetworks-aggregated.json \

include ../Makefile.inc

json-dumps/datafusion-instances.json:
	$(CURL) -fsS \
	  	'https://datafusion.googleapis.com/v1/projects/$(PROJECT_ID)/locations/-/instances' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-service-account-policy.json:
	$(CURL) -fsS \
	  'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/serviceAccounts/$(SERVICE_ACCOUNT):getIamPolicy' \
	  | $(JSON_CLEANER) service-accounts \
	  | $(SED_SUBST_FAKE) >$@
