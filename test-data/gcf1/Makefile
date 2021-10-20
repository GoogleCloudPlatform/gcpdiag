PROJECT_ID  := $(shell terraform output project_id | sed -e 's|"||g')
PROJECT_NR  := 778405515516
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = us-central1
REGION_2     = asia-east1

all:	\
	json-dumps/cloudfunctions.json \
	json-dumps/cloudfunctions-$(REGION_1).json \
	json-dumps/cloudfunctions-empty.json \
	json-dumps/project.json \
	json-dumps/services.json

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' >$@

json-dumps/services.json:
	$(CURL) -fsS \
	  'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' >$@

json-dumps/cloudfunctions.json:
	$(CURL) -fsS \
	  'https://cloudfunctions.googleapis.com/v1/projects/$(PROJECT_ID)/locations/-/functions' \
	  | $(JSON_CLEANER) cloudfunctions >$@

json-dumps/cloudfunctions-$(REGION_1).json:
	$(CURL) -fsS \
	  'https://cloudfunctions.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_1)/functions' \
	  | $(JSON_CLEANER) cloudfunctions >$@

json-dumps/cloudfunctions-empty.json:
	$(CURL) -fsS \
	  'https://cloudfunctions.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_2)/functions' \
	  | $(JSON_CLEANER) cloudfunctions >$@
