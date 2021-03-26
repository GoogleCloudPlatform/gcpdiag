PROJECT_ID  := $(shell terraform output project_id | sed -e 's|"||g')
PROJECT_NR  := 18404348413
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = europe-west1
ZONE_1       = europe-west4-a

# Execute all lines in a single bash session.
#.ONESHELL:
#SHELL=/bin/bash
#.SHELLFLAGS=-e

all:	json-dumps/clusters.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-roles-custom.json \
	json-dumps/iam-roles-predefined-1.json.gz \
	json-dumps/iam-roles-predefined-2.json.gz \
 	json-dumps/project.json

json-dumps/clusters.json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/locations/-/clusters' \
		| $(JSON_CLEANER) clusters >$@

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID)' >$@

json-dumps/iam-policy.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID):getIamPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "" \
		| $(JSON_CLEANER) other >$@

json-dumps/iam-roles-predefined-1.json.gz:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/roles?view=FULL&pageSize=500' | gzip -c >$@

json-dumps/iam-roles-predefined-2.json.gz: json-dumps/iam-roles-predefined-1.json.gz
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/roles?view=FULL&pageSize=500&pageToken=$(shell zcat json-dumps/iam-roles-predefined-1.json.gz | jq -r '.nextPageToken')' | gzip -c >$@

json-dumps/iam-roles-custom.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/roles?view=FULL&pageSize=500' >$@

json-dumps/server-config-region-1.json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_1)/serverConfig' >$@

json-dumps/server-config-zone-1.json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/serverconfig' >$@

# Note: this throws an error. See also: b/175212189
#  "code": 403,
#  "message": "Your application has authenticated using end user credentials
#  from the Google Cloud SDK or Google Cloud Shell which are not supported by
#  the policytroubleshooter.googleapis.com. We recommend configuring the
#  billing/quota_project setting in gcloud or using a service account through
#  the auth/impersonate_service_account setting. For more information about
#  service accounts and how to use them in your application, see
#  https://cloud.google.com/docs/authentication/.",
#json-dumps/iam-troubleshoot-ok.json:
#	$(CURL) -fsS \
#               https://policytroubleshooter.googleapis.com/v1/iam:troubleshoot \
#                -X POST  --header "Content-Type:text/json" \
#               -d @- <<DATA
#	{
#	  "accessTuple": {
#	      "principal": "$(PROJECT_NR)-compute@developer.gserviceaccount.com",
#	      "fullResourceName": "//container.googleapis.com/projects/$(PROJECT_ID)/clusters/gke1",
#	      "permission": "logging.logEntries.create"
#	  }
#	}
#	DATA
