PROJECT_ID := $(shell terraform output project_id | sed -e 's|"||g')
PROJECT_ID_SUFFIX := $(shell terraform output -json project_id_suffix)
PROJECT_NR  := $(shell terraform output -json project_nr)
ORG_ID      := $(shell terraform output -json org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
LOCATION     = us-west1-a
REGION       = us-west1
INSTANCE_OK_NAME = notebooks2instance-ok
INSTANCE_PROVISIONING_STUCK_NAME = notebooks2instance-provisioning-stuck

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340012
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

ORG_POLICY_CONSTRAINTS = \
	json-dumps/org-constraint-compute.disableSerialPortAccess.json \
	json-dumps/org-constraint-compute.requireOsLogin.json \
  json-dumps/org-constraint-compute.requireShieldedVm.json \
	json-dumps/org-constraint-iam.automaticIamGrantsForDefaultServiceAccounts.json \
	json-dumps/org-constraint-compute.disableSerialPortLogging.json  \
	json-dumps/org-constraint-compute.disableSshInBrowser.json

define MONITORING_QUERY
{ \
  "query": "fetch gce_instance \
            | metric 'compute.googleapis.com/instance/cpu/utilization' \
            | group_by 5m, [value_utilization_max: max(value.utilization)] \
            | every 5m \
  					" \
}
endef

define LOGGING_ENTRIES_BODY
{ \
	"resourceNames": ["projects/$(PROJECT_ID)"], \
	"orderBy": "timestamp desc", \
	"filter": " \
		timestamp > \"2024-06-24T23:00:00+00:00\" AND \
		timestamp < \"2024-06-25T07:00:00+00:00\" AND \
		resource.type=\"gce_instance\" \
	" \
}
endef

all:	\
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/compute-serial-port-output-$(INSTANCE_OK_NAME).json \
	json-dumps/compute-serial-port-output-$(INSTANCE_PROVISIONING_STUCK_NAME).json \
	json-dumps/compute-instances-us-west1-a.json \
	json-dumps/compute-instances-disks-us-west1-a.json \
	json-dumps/workbench-instances.json \
	json-dumps/notebooks2instance-ok-check-upgradability.json \
	json-dumps/notebooks2instance-ok-check-upgradability.json \
	json-dumps/notebooks2instance-provisioning-stuck-check-upgradability.json \
	json-dumps/monitoring-query.json \
	json-dumps/logging-entries-1.json \
	$(ORG_POLICY_CONSTRAINTS)

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/services.json:
	$(CURL) -fv \
	'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
	| $(SED_SUBST_FAKE) >$@

json-dumps/org-constraint-%.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID):getEffectiveOrgPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "{\"constraint\": \"constraints/$*\"}" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

json-dumps/monitoring-query.json:
	$(CURL) -fsS \
		'https://monitoring.googleapis.com/v3/projects/$(PROJECT_ID)/timeSeries:query' \
		--header "Content-Type: application/json" -X POST \
		--data '$(MONITORING_QUERY)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-us-west1-a.json:
	$(CURL) -fv \
		'https://compute.googleapis.com/compute/v1/projects/${PROJECT_ID}/zones/${LOCATION}/instances' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-disks-us-west1-a.json:
	$(CURL) -fv \
		'https://compute.googleapis.com/compute/v1/projects/${PROJECT_ID}/zones/${LOCATION}/disks' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-serial-port-output-%.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$(LOCATION)/instances/$*/serialPort?start=-1000000' \
		--header "Content-Type:text/json" \
		| $(SED_SUBST_FAKE) >$@

json-dumps/workbench-instances.json:
	$(CURL) -fv \
		'https://notebooks.googleapis.com/v2/projects/${PROJECT_ID}/locations/${LOCATION}/instances' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/notebooks2instance-ok-check-upgradability.json:
	$(CURL) -fv \
		'https://notebooks.googleapis.com/v2/projects/${PROJECT_ID}/locations/${LOCATION}/instances/${INSTANCE_OK_NAME}:checkUpgradability' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/notebooks2instance-provisioning-stuck-check-upgradability.json:
	$(CURL) -fv \
		'https://notebooks.googleapis.com/v2/projects/${PROJECT_ID}/locations/${LOCATION}/instances/${INSTANCE_PROVISIONING_STUCK_NAME}:checkUpgradability' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/logging-entries-1.json:
	$(CURL) -fsS \
		'https://logging.googleapis.com/v2/entries:list' \
		--header "Content-Type:text/json" \
		--data '$(LOGGING_ENTRIES_BODY)' \
		| $(SED_SUBST_FAKE) >$@
