PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340009
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
				-e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
				-e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/project.json \
	json-dumps/compute-interconnects.json \
	json-dumps/compute-project.json

include ../Makefile.inc
