PROJECT_ID := $(shell terraform output project_id | sed -e 's|"||g')
PROJECT_ID_SUFFIX := $(shell terraform output -json project_id_suffix)
PROJECT_NR  := $(shell terraform output -json project_nr)
ORG_ID      := $(shell terraform output -json org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
LOCATION     = us-west1-a
INSTANCE_NAME = gcpdiag-notebooks1instance-aaaa

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340012
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/instances.json \
	json-dumps/health-state.json \

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fv \
	'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/instances.json:
	$(CURL) -fv \
		'https://notebooks.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/instances' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/health-state.json:
	$(CURL) -fv \
		'https://notebooks.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/instances/${INSTANCE_NAME}:getInstanceHealth' \
		| $(SED_SUBST_FAKE) >$@
