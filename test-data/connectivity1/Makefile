PROJECT_ID  := $(shell terraform output  project_id)
PROJECT_ID_SUFFIX := $(shell terraform output  project_id_suffix)
PROJECT_NR  := $(shell terraform output project_nr)
ORG_ID      := $(shell terraform output org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = us-central1

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340017
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \


all:	\
	json-dumps/services.json \
	json-dumps/project.json \
	json-dumps/operations

include ../Makefile.inc
