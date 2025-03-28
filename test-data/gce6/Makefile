PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
ZONE_1       = us-central1-c

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 1234560123456
FAKE_ORG_ID = 11112222

COMPUTE_INSTANCES_MAXRESULTS=3

INSTANCE_NAME_GCE1=existing-instance
INSTANCE_NAME_GCE2=non-existing-gpu-instance
START_TIMESTAMP = 2025-03-28T00:00:00+00:00
END_TIMESTAMP   = 2025-03-29T00:00:00+00:00

SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \
		     -e "s/[a-zA-Z0-9._%+-]+@google.com/$(FAKE_USER_ACCOUNT)/"

all:	\
	json-dumps/compute-effective-firewalls-default.json \
	json-dumps/compute-instances-$(ZONE_1).json \
	json-dumps/compute-disks-$(ZONE_1).json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-project.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/global-operations.json \
	json-dumps/logging-entries-1.json \
	json-dumps/compute-migs-aggregated.json \
	json-dumps/healthChecks.json \
	json-dumps/compute-instances-aggregated.json

include ../Makefile.inc


TERMINATION_OPERATION_FILTER="%28operationType%3D%22compute.instances.repair.recreateInstance%22%29%20OR%20%28operationType%3D%22compute.instances.hostError%22%29%20OR%20%28operationType%3D%22compute.instances.guestTerminate%22%29%20OR%20%28operationType%3D%22compute.instances.preempted%22%29%20OR%20%28operationType%3D%22compute.instances.terminateOnHostMaintenance%22%29%20OR%20%28operationType%3D%22stop%22%29%20OR%20%28operationType%3D%22suspend%22%29%20OR%20%28operationType%3D%22reset%22%29%20OR%20%28operationType%3D%22compute.instanceGroupManagers.resizeAdvanced%22%29%20OR%20%28operationType%3D%22compute.autoscalers.resize%22%29%0A"
json-dumps/global-operations.json:
	$(CURL) -fsS \
	  "https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/aggregated/operations?filter=$(TERMINATION_OPERATION_FILTER)" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

# 	protoPayload.methodName=~\"compute.instances.(hostError|guestTerminate|preempted|terminateOnHostMaintenance|stop|suspend|repair.recreateInstance|ScheduledVMs)\" OR
define LOGGING_ENTRIES_BODY
{
	"resourceNames": ["projects/$(PROJECT_ID)"],
	"orderBy": "timestamp desc",
	"pageSize": 200,
	"filter": "resource.type=\"gce_instance\" AND
	log_id(\"cloudaudit.googleapis.com/activity\") AND
	(protoPayload.resourceName=\"projects/$(PROJECT_ID)/zones/$(ZONE_1)/instances/$(INSTANCE_NAME_GCE1)\" OR protoPayload.resourceName=\"projects/$(PROJECT_ID)/zones/$(ZONE_1)/instances/$(INSTANCE_NAME_GCE2)\") AND
	protoPayload.methodName=~\"compute.instances.insert\" AND
	severity=\"ERROR\" AND
	(protoPayload.status.message=\"QUOTA_EXCEEDED\" OR
	protoPayload.response.error.errors.reason=\"alreadyExists\" OR
	protoPayload.response.error.message=~\"Required '.*' permission for '.*'\")"
}
endef

export LOGGING_ENTRIES_BODY

json-dumps/logging-entries-1.json:
	$(CURL) -fsS \
		'https://logging.googleapis.com/v2/entries:list' \
		--header "Content-Type:text/json" \
		-d "$$LOGGING_ENTRIES_BODY" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

json-dumps/healthChecks.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/healthChecks/' \
		| $(SED_SUBST_FAKE) >$@
