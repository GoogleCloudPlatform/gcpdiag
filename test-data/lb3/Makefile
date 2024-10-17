#!/bin/bash
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

REGION1 = europe-west4

ZONE1 = us-east1-b
ZONE2 = europe-west4-b

all:	\
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/forwardingRules.json \
	json-dumps/compute-sslCertificates.json \
	json-dumps/compute-aggregated-targetHttpsProxies.json \
	json-dumps/compute-targetSslProxies.json \
	json-dumps/logging-entries-1.json

include ../Makefile.inc

# If you need to recreate the JSON: adapt the timestamp and make sure that there are some entries found.
define LOGGING_ENTRIES_BODY
{
	"resourceNames": ["projects/$(PROJECT_ID)"],
	"orderBy": "timestamp desc",
	"filter": "
		resource.type=\"gce_target_https_proxy\"
		resource.labels.target_https_proxy_id=\"2209022440749649672\"
		protoPayload.methodName=~\"targetHttpsProxies.(patch|update|insert|setSslCertificates)\"
	"
}
endef
export LOGGING_ENTRIES_BODY

json-dumps/logging-entries-1.json:
	$(CURL) -fsS \
		'https://logging.googleapis.com/v2/entries:list' \
		--header "Content-Type:text/json" \
		-d "$$LOGGING_ENTRIES_BODY" \
		| $(SED_SUBST_FAKE) >$@

json-dumps/forwardingRules.json:
	@$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/aggregated/forwardingRules/' \
		| $(SED_SUBST_FAKE) > $@
	@python3 update_ip.py < "$@" > temp2.json && mv temp2.json "$@"
