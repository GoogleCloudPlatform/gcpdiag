PROJECT_ID  := $(shell terraform output project_id | sed -e 's|"||g')
FAKE_PROJECT_ID = composer1
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = us-central1

all:	\
	json-dumps/compute-regions.json \
	json-dumps/services.json \
	json-dumps/composer-environments-$(REGION_1).json

json-dumps/compute-regions.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions' \
	| sed 's/$(PROJECT_ID)/$(FAKE_PROJECT_ID)/g' \
	>$@

json-dumps/services.json:
	$(CURL) -fsS \
	  'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	>$@

json-dumps/composer-environments-$(REGION_1).json:
	$(CURL) -fsS \
	  'https://composer.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_1)/environments' \
	| sed 's/$(PROJECT_ID)/$(FAKE_PROJECT_ID)/g' \
	>$@
