PROJECT_ID  := $(shell /google/data/ro/teams/terraform/bin/terraform output project_id)
PROJECT_ID_SUFFIX := $(shell terraform output project_id_suffix)
PROJECT_NR  := $(shell terraform output project_nr)
ORG_ID      := $(shell terraform output org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION = us-central1
STREAMING_JOB := $(shell terraform output job_id)

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340010
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/services.json \
	json-dumps/dataflow-jobs-${REGION}.json \
	json-dumps/dataflow-jobs-${REGION}-streaming.json \
	json-dumps/log-exclusions.json

include ../Makefile.inc

json-dumps/dataflow-jobs-${REGION}.json:
	$(CURL) -fsS \
		"https://dataflow.googleapis.com/v1b3/projects/${PROJECT_ID}/locations/${REGION}/jobs" \
		| $(SED_SUBST_FAKE) >$@

json-dumps/dataflow-jobs-${REGION}-streaming.json:
	$(CURL) -fsS \
		"https://dataflow.googleapis.com/v1b3/projects/${PROJECT_ID}/locations/${REGION}/jobs/${STREAMING_JOB}" \
		| $(SED_SUBST_FAKE) >$@

json-dumps/log-exclusions.json:
	$(CURL) -fsS \
		"https://logging.googleapis.com/v2/projects/${PROJECT_ID}/exclusions" \
		| $(SED_SUBST_FAKE) >$@
