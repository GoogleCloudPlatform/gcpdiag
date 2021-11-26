PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = us-central1
REGION_2     = asia-east1

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340003
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/cloudfunctions.json \
	json-dumps/cloudfunctions-$(REGION_1).json \
	json-dumps/cloudfunctions-empty.json \
	json-dumps/project.json \
	json-dumps/services.json

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fsS \
	        'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/cloudfunctions.json:
	$(CURL) -fsS \
	  'https://cloudfunctions.googleapis.com/v1/projects/$(PROJECT_ID)/locations/-/functions' \
		| $(JSON_CLEANER) cloudfunctions \
		| $(SED_SUBST_FAKE) >$@

json-dumps/cloudfunctions-$(REGION_1).json:
	$(CURL) -fsS \
	  'https://cloudfunctions.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_1)/functions' \
		| $(JSON_CLEANER) cloudfunctions \
		| $(SED_SUBST_FAKE) >$@

json-dumps/cloudfunctions-empty.json:
	$(CURL) -fsS \
	  'https://cloudfunctions.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_2)/functions' \
		| $(JSON_CLEANER) cloudfunctions \
		| $(SED_SUBST_FAKE) >$@
