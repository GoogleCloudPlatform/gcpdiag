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
	json-dumps/services.json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-project.json \
	json-dumps/compute-regions.json \
	json-dumps/compute-backendServices.json \
	json-dumps/compute-aggregated-backendServices.json \
	json-dumps/compute-aggregated-forwardingRules.json \
	json-dumps/healthChecks.json \

include ../Makefile.inc


json-dumps/healthChecks.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/healthChecks/' \
		| $(SED_SUBST_FAKE) >$@
