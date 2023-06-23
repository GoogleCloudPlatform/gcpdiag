PROJECT_ID := $(shell terraform output project_id | sed -e 's|"||g')
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
APIGEE_ORG_ID  := $(shell terraform output apigee_org_id | sed -e 's|"||g')
APIGEE_INSTANCE_ID  := $(shell terraform output apigee_instance_id | sed -e 's|"||g')
LOCATION_1 = us-central1
KEYRING_1 = apigee-keyring
CYRPTOKEY_1 = apigee-key
COMPUTE_NETWORK_1=apigee-network
COMPUTE_SUBNETWORK_1=apigee-subnetwork
ENVIRONMENT_GROUP = gcpdiag-demo-envgroup
ENVIRONMENT_GROUP_1 = gcpdiag-demo-envgroup-1
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340005
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

all:	\
	json-dumps/apigee-organizations.json \
	json-dumps/apigee-organization.json \
	json-dumps/compute-regions.json \
	json-dumps/compute-subnetworks-aggregated.json \
	json-dumps/compute-effective-firewalls-apigee-network.json \
	json-dumps/compute-network-$(COMPUTE_NETWORK_1).json \
	json-dumps/compute-subnetworks-$(COMPUTE_SUBNETWORK_1).json \
	json-dumps/apigee-instances.json \
	json-dumps/compute-templates.json  \
	json-dumps/compute-migs-$(LOCATION_1).json  \
	json-dumps/apigee-instances-gcpdiag-apigee1-inst1-aaaa-attachments.json \
	json-dumps/apigee-envgroups.json   \
    json-dumps/apigee-envgroups-attachments-empty.json   \
	json-dumps/apigee-envgroups-gcpdiag-demo-envgroup-1-attachments.json    \
	json-dumps/project.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/services.json \
	json-dumps/kms-key-iam-policy.json \
	json-dumps/apigee-key.json

include ../Makefile.inc

# compute.googleapis.com
json-dumps/compute-migs-$(LOCATION_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$(LOCATION_1)/instanceGroupManagers' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-subnetworks-$(COMPUTE_SUBNETWORK_1).json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$(LOCATION_1)/subnetworks/$(COMPUTE_SUBNETWORK_1)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-effective-firewalls-apigee-network.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/networks/$(COMPUTE_NETWORK_1)/getEffectiveFirewalls' \
		| $(SED_SUBST_FAKE) >$@

# cloudkms.googleapis.com

json-dumps/kms-key-iam-policy.json:
	$(CURL) -fsS \
	  'https://cloudkms.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(LOCATION_1)/keyRings/$(KEYRING_1)/cryptoKeys/$(CYRPTOKEY_1):getIamPolicy' \
	  | $(JSON_CLEANER) other \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/apigee-key.json:
	$(CURL) -fsS \
	  'https://cloudkms.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(LOCATION_1)/keyRings/$(KEYRING_1)/cryptoKeys/$(CYRPTOKEY_1)' \
	  | $(SED_SUBST_FAKE) >$@

# apigee.googleapis.com

json-dumps/apigee-organizations.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/organizations'  \
		| $(SED_SUBST_FAKE) >$@

json-dumps/apigee-organization.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/$(APIGEE_ORG_ID)'  \
		| $(JSON_CLEANER) apigee \
		| $(SED_SUBST_FAKE) >$@

json-dumps/apigee-instances.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/$(APIGEE_ORG_ID)/instances'  \
		| $(SED_SUBST_FAKE) >$@

json-dumps/apigee-instances-gcpdiag-apigee1-inst1-aaaa-attachments.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/$(APIGEE_INSTANCE_ID)/attachments'  \
		| $(SED_SUBST_FAKE) >$@

json-dumps/apigee-envgroups.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/$(APIGEE_ORG_ID)/envgroups'  \
		| $(SED_SUBST_FAKE) >$@

json-dumps/apigee-envgroups-attachments-empty.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/$(APIGEE_ORG_ID)/envgroups/$(ENVIRONMENT_GROUP)/attachments'  \
		| $(SED_SUBST_FAKE) >$@

json-dumps/apigee-envgroups-gcpdiag-demo-envgroup-1-attachments.json:
	$(CURL) -fsS \
		'https://apigee.googleapis.com/v1/$(APIGEE_ORG_ID)/envgroups/$(ENVIRONMENT_GROUP_1)/attachments'  \
		| $(SED_SUBST_FAKE) >$@
