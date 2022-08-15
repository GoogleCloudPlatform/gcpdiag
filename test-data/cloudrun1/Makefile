PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = us-central1

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 123400010
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/locations.json \
	json-dumps/cloudrun_services.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/project.json \
	json-dumps/services.json

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fv \
	        'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/cloudrun_services.json:
	$(CURL) -fsS \
	  'https://run.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_1)/services' \
		| $(JSON_CLEANER) cloudrun \
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

json-dumps/locations.json:
	$(CURL) -fsS \
	  'https://run.googleapis.com/v1/projects/$(PROJECT_ID)/locations' \
		| $(SED_SUBST_FAKE) >$@
