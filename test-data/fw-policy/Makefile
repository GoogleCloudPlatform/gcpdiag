PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
FOLDER_ID_1 := $(shell terraform output -raw folder_id_1)
FOLDER_ID_2 := $(shell terraform output -raw folder_id_2)

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340004
FAKE_ORG_ID = 11112222
FAKE_FOLDER_ID_1 = 100001
FAKE_FOLDER_ID_2 = 100002

ORG_POLICY_CONSTRAINTS = \
	json-dumps/org-constraint-compute.disableSerialPortAccess.json \
	json-dumps/org-constraint-compute.requireOsLogin.json \
	json-dumps/org-constraint-compute.requireShieldedVm.json

all:	\
	json-dumps/compute-effective-firewalls-default.json \
	json-dumps/compute-instances-europe-west1-b.json \
	json-dumps/compute-instances-empty.json \
	json-dumps/compute-migs-europe-west1-b.json \
	json-dumps/compute-migs-empty.json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-project.json \
	json-dumps/compute-subnetworks-europe-west4.json \
	json-dumps/compute-zones.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-roles-custom.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/project.json \
	json-dumps/services.json \
	$(ORG_POLICY_CONSTRAINTS)

include ../Makefile.inc
