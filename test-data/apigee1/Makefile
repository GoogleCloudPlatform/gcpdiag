PROJECT_ID := $(shell terraform output project_id | sed -e 's|"||g')
APIGEE_ORG_ID  := $(shell terraform output apigee_org_id | sed -e 's|"||g')
ENVIRONMENT_GROUP = gcpdiag-demo-envgroup
ENVIRONMENT_GROUP_1 = gcpdiag-demo-envgroup-1
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

all:	\
	json-dumps/apigee-organizations.json \
	json-dumps/environment-groups.json   \
  json-dumps/environment-group-empty-attachments.json   \
	json-dumps/environment-group-attachments.json    \
	json-dumps/project.json \
	json-dumps/services.json

# cloudresourcemanager.googleapis.com

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' >$@

# serviceusage.googleapis.com

json-dumps/services.json:
	$(CURL) -fsS \
	  'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' >$@

# apigee.googleapis.com

json-dumps/apigee-organizations.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/organizations' >$@

json-dumps/environment-groups.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/$(APIGEE_ORG_ID)/envgroups' >$@

json-dumps/environment-group-empty-attachments.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/$(APIGEE_ORG_ID)/envgroups/$(ENVIRONMENT_GROUP)/attachments' >$@

json-dumps/environment-group-attachments.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/$(APIGEE_ORG_ID)/envgroups/$(ENVIRONMENT_GROUP_1)/attachments' >$@
