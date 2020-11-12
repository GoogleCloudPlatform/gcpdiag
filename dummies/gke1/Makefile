PROJECT_ID  := $(shell terraform output project_id)
CURL_GET     = ../../bin/curl-get-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

all: json-dumps/clusters.json

json-dumps/clusters.json:
	$(CURL_GET) -fsS \
		https://container.googleapis.com/v1/projects/$(PROJECT_ID)/locations/-/clusters \
		| $(JSON_CLEANER) clusters >$@
