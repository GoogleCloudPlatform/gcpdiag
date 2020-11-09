PROJECT_ID := $(shell terraform output project_id)

all: json-dumps/clusters.json

json-dumps/clusters.json:
	../../bin/curl-get-wrap.sh https://container.googleapis.com/v1/projects/$(PROJECT_ID)/locations/-/clusters >$@
