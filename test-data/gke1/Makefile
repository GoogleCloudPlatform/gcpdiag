PROJECT_ID  := $(shell terraform output project_id | sed -e 's|"||g')
PROJECT_NR  := 18404348413
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
REGION_1     = europe-west1
ZONE_1       = europe-west4-a
ZONE_EMPTY   = europe-west4-b

# Execute all lines in a single bash session.
#.ONESHELL:
#SHELL=/bin/bash
#.SHELLFLAGS=-e

all:	\
	json-dumps/container-clusters.json \
	json-dumps/container-server-config-$(REGION_1).json \
	json-dumps/container-server-config-$(ZONE_1).json \
	json-dumps/compute-instances-$(ZONE_1).json \
	json-dumps/compute-instances-empty.json \
	json-dumps/compute-migs-$(ZONE_1).json \
	json-dumps/compute-migs-empty.json \
	json-dumps/compute-project.json \
	json-dumps/compute-zones.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-roles-custom.json \
	json-dumps/iam-roles-predefined-1.json.gz \
	json-dumps/iam-roles-predefined-2.json.gz \
 	json-dumps/project.json

# compute.googleapis.com

json-dumps/compute-zones.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones' >$@

json-dumps/compute-instances-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instances' \
		| $(JSON_CLEANER) instances >$@

json-dumps/compute-migs-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/instanceGroupManagers' \
		 >$@

json-dumps/compute-instances-empty.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_EMPTY)/instances' \
		| $(JSON_CLEANER) instances >$@

json-dumps/compute-migs-empty.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(ZONE_EMPTY)/instanceGroupManagers' \
		| $(JSON_CLEANER) instances >$@

json-dumps/compute-project.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)' >$@


# cloudresourcemanager.googleapis.com

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' >$@

json-dumps/iam-policy.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID):getIamPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "" \
		| $(JSON_CLEANER) other >$@

# iam.googleapis.com

json-dumps/iam-roles-predefined-1.json.gz:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/roles?view=FULL&pageSize=500' | gzip -c >$@

json-dumps/iam-roles-predefined-2.json.gz: json-dumps/iam-roles-predefined-1.json.gz
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/roles?view=FULL&pageSize=500&pageToken=$(shell zcat json-dumps/iam-roles-predefined-1.json.gz | jq -r '.nextPageToken')' | gzip -c >$@

json-dumps/iam-roles-custom.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/roles?view=FULL&pageSize=500' >$@

# container.googleapis.com

json-dumps/clusters.json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/locations/-/clusters' \
		| $(JSON_CLEANER) clusters >$@

json-dumps/container-server-config-$(REGION_1).json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION_1)/serverConfig' >$@

json-dumps/container-server-config-$(ZONE_1).json:
	$(CURL) -fsS \
		'https://container.googleapis.com/v1/projects/$(PROJECT_ID)/zones/$(ZONE_1)/serverconfig' >$@

# servicemanagement.googleapis.com

json-dumps/services.json:
	$(CURL) -fsS \
		'https://servicemanagement.googleapis.com/v1/services?consumerId=project:$(PROJECT_ID)' >$@


# If you need to recreate the JSON: adapt the timestamp and make sure that there are some entries found.
define LOGGING_ENTRIES_BODY
{
	"resourceNames": ["projects/$(PROJECT_ID)"],
	"orderBy": "timestamp desc",
	"filter": "
		timestamp > \"2021-06-17T10:00:00+00:00\" AND
		timestamp < \"2021-06-18T10:00:00+00:00\" AND
		resource.type=\"gce_instance_group_manager\" AND
		protoPayload.methodName=\"beta.compute.instanceGroupManagers.createInstances\" AND
		operation.last=\"true\" AND
		log_name=\"projects/$(PROJECT_ID)/logs/cloudaudit.googleapis.com%2Factivity\"
	"
}
endef
export LOGGING_ENTRIES_BODY

json-dumps/logging-entries-1.json:
	$(CURL) --trace trace.log \
		'https://logging.googleapis.com/v2/entries:list' \
		--header "Content-Type:text/json" \
		-d "$$LOGGING_ENTRIES_BODY" >$@


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
