PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_NR  := $(shell terraform output -raw project_nr)
FOLDER_ID   := $(shell terraform output -raw folder_id)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

LOCATION = us-central1

FAKE_PROJECT_ID = cloudasset1-test-project
FAKE_PROJECT_NR = 12340071
FAKE_FOLDER_ID = 9898989
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID)/$(FAKE_PROJECT_ID)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \
				 -e "s/$(FOLDER_ID)/$(FAKE_FOLDER_ID)/"

all:	\
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/search-all-resources-$(LOCATION).json \

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fv \
	'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/search-all-resources-$(LOCATION).json:
	$(CURL) -fsS \
	    --header "x-goog-user-project: $(PROJECT_ID)" \
	    'https://cloudasset.googleapis.com/v1/projects/$(PROJECT_ID):searchAllResources?query=$(LOCATION)' \
			| $(SED_SUBST_FAKE) >$@
