PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)

CLUSTER = cluster-1

CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION     = us-central1
ZONE       = us-central1-c

FAKE_PROJECT_ID_SUFFIX = gggg
FAKE_PROJECT_NR = 12340032
FAKE_ORG_ID = 11112232
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/container-cluster-$(CLUSTER).json \
	json-dumps/logging-entries-1.json \
	json-dumps/logging-entries-2.json \
	json-dumps/services.json \
	json-dumps/project.json


include ../Makefile.inc


json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@


json-dumps/services.json:
	$(CURL) -fsS \
	        'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
		| $(SED_SUBST_FAKE) >$@


json-dumps/container-cluster-$(CLUSTER).json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(ZONE)/clusters/$(CLUSTER)' \
		| $(JSON_CLEANER) clusters \
		| $(SED_SUBST_FAKE) >$@


# If you need to recreate the JSON: adapt the timestamp and make sure that there are some entries found.
define LOGGING_ENTRIES_BODY
{
	"resourceNames": ["projects/$(PROJECT_ID)"],
	"orderBy": "timestamp desc",
	"filter": "
		timestamp > \"2024-06-30T01:00:00+00:00\" AND
		timestamp < \"2024-06-30T23:00:00+00:00\" AND
		\"IP_SPACE_EXHAUSTED\" AND \"$(CLUSTER)\"
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


define LOGGING_ENTRIES_BODY_1
{
	"resourceNames": ["projects/$(PROJECT_ID)"],
	"orderBy": "timestamp desc",
	"filter": "
		timestamp > \"2024-06-30T01:00:00+00:00\" AND
		timestamp < \"2024-06-30T23:00:00+00:00\" AND
		jsonPayload.resourceName=\"//container.googleapis.com/projects/$(PROJECT_ID)/zones/us-central1-c/clusters/$(CLUSTER)\" AND
		logName=\"projects/$(PROJECT_ID)/logs/networkanalyzer.googleapis.com%2Fanalyzer_reports\"
	"
}
endef
export LOGGING_ENTRIES_BODY_1

json-dumps/logging-entries-2.json:
	$(CURL) -fsS \
		'https://logging.googleapis.com/v2/entries:list' \
		--header "Content-Type:text/json" \
		-d "$$LOGGING_ENTRIES_BODY_1" \
		| $(SED_SUBST_FAKE) >$@
