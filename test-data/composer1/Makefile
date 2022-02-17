PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
ENV2_SA     := $(shell terraform output -raw env2_sa)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = us-central1

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340005
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/compute-regions.json \
	json-dumps/services.json \
	json-dumps/composer-environments-$(REGION_1).json \
	json-dumps/project.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/iam-service-account-policy.json

json-dumps/compute-regions.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fsS \
	  'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/composer-environments-$(REGION_1).json:
	$(CURL) -fsS \
	  'https://composer.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_1)/environments' \
	| $(SED_SUBST_FAKE) >$@

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

json-dumps/iam-service-accounts.json:
	$(CURL) -fsS \
	  'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/serviceAccounts' \
	  | $(JSON_CLEANER) service-accounts \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/iam-service-account-policy.json:
	$(CURL) -fsS \
	  'https://iam.googleapis.com/v1/$(ENV2_SA):getIamPolicy' \
	  -X POST  --header "Content-Type:text/json" \
	  -d "" \
	  | $(JSON_CLEANER) other \
	  | $(SED_SUBST_FAKE) >$@
