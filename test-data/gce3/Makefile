PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
ZONE_1       = europe-west2-a

FAKE_PROJECT_ID_SUFFIX = 'ops-agent'
FAKE_PROJECT_NR = 12345001
FAKE_ORG_ID = 11112222

COMPUTE_INSTANCES_MAXRESULTS=3

INSTANCE_NAME_GCE2=working-opsagent
INSTANCE_NAME_GCE1=faulty-opsagent

ORG_POLICY_CONSTRAINTS = \
	json-dumps/org-constraint-compute.disableSerialPortAccess.json \
  json-dumps/org-constraint-compute.requireOsLogin.json \
  json-dumps/org-constraint-compute.requireShieldedVm.json \
  json-dumps/org-constraint-iam.automaticIamGrantsForDefaultServiceAccounts.json \
  json-dumps/org-constraint-compute.disableSerialPortLogging.json \
  json-dumps/org-constraint-compute.disableSshInBrowser.json


all:	\
	json-dumps/compute-effective-firewalls-default.json \
	json-dumps/compute-instances-$(ZONE_1).json \
	json-dumps/compute-instances-empty.json \
	json-dumps/compute-disks-empty.json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-project.json \
	json-dumps/compute-regions.json \
	json-dumps/compute-zones.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/monitoring-query.json \
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/iam-roles-get.json \
	json-dumps/iam-roles-custom.json \
  json-dumps/predefined-roles.json \
  ORG_POLICY_CONSTRAINTS
include ../Makefile.inc

define MONITORING_QUERY
{ \
  "query": "fetch gce_instance::compute.googleapis.com/instance/uptime_total \
  | within 10m \
  | group_by [resource.zone, metric.instance_name] \
  | group_by 5m, [.mean, .count] \
  " \
}
endef
json-dumps/monitoring-query.json:
	$(CURL) -fsS \
		'https://monitoring.googleapis.com/v3/projects/$(PROJECT_ID)/timeSeries:query' \
		--header "Content-Type: application/json" -X POST \
		--data '$(MONITORING_QUERY)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-roles-get.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/roles/logging.admin' \
		| $(SED_SUBST_FAKE) \
		| jq '{"roles": [.]}' >$@

json-dumps/iam-roles-custom.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/roles?view=FULL&pageSize=500' \
		| $(SED_SUBST_FAKE) >$@
