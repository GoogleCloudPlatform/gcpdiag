
PROJECT_ID := $(shell terraform output project_id | sed -e 's|"||g')
PROJECT_NR  := $(shell terraform output -json project_nr | sed -e 's|"||g')
FOLDER_ID  := $(shell terraform output -json folder_id | sed -e 's|"||g')
ORG_ID      := $(shell terraform output -json org_id | sed -e 's|"||g')
INSTANCE = $(shell terraform output -json instance_name | sed -e 's|"||g')
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
LOCATION     = us-central1-a
FAKE_FOLDER_ID = 9839384
FAKE_PROJECT_ID = fake-project
FAKE_PROJECT_NR = 12340051
FAKE_ORG_ID = 11112222
FAKE_INSTANCE_NAME = fake-instance
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID)/$(FAKE_PROJECT_ID)/" \
				-e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
				-e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \
				-e "s/$(FOLDER_ID)/$(FAKE_FOLDER_ID)/" \
				-e "s/$(INSTANCE)/$(FAKE_INSTANCE_NAME)/" \

all:	\
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/inventory.json \

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fv \
	'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/inventory.json:
	$(CURL) -fv \
		'https://osconfig.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/instances/${INSTANCE}/inventory?view=full' \
		| $(SED_SUBST_FAKE) >$@
