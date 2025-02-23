# This makefile include file assumes that the following variables are set:
# - PROJECT_ID
# - PROJECT_ID_SUFFIX
# - PROJECT_NR
# - ORG_ID
# - FAKE_PROJECT_ID_SUFFIX
# - FAKE_PROJECT_NR
# - FAKE_ORG_ID

BASEDIR := ../..
JSON_CLEANER = $(BASEDIR)/bin/json-cleaner
CURL         = $(BASEDIR)/bin/curl-wrap.sh
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
		     -e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
		     -e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \
                     $(if $(FOLDER_ID_1),-e "s/$(FOLDER_ID_1)/$(FAKE_FOLDER_ID_1)/") \
		     $(if $(FOLDER_ID_2),-e "s/$(FOLDER_ID_2)/$(FAKE_FOLDER_ID_2)/")
ZONE_EMPTY = europe-west2-b
ACCESS_TOKEN := $(shell gcloud auth application-default print-access-token)
export ACCESS_TOKEN

# compute.googleapis.com

json-dumps/compute-effective-firewalls-%.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/networks/$*/getEffectiveFirewalls' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-igs-%.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$*/instanceGroups' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-igs-empty.json: json-dumps/compute-igs-$(ZONE_EMPTY).json
	ln -sf $(notdir $<) $@

json-dumps/compute-negs-%.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$*/networkEndpointGroups' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-nes-empty.json: json-dumps/compute-negs-$(ZONE_EMPTY).json
	ln -sf $(notdir $<) $@

COMPUTE_INSTANCES_MAXRESULTS ?= 10

json-dumps/compute-instances-%.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$*/instances?maxResults=$(COMPUTE_INSTANCES_MAXRESULTS)' \
		| $(JSON_CLEANER) instances \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-%-2.json: json-dumps/compute-instances-%.json
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$*/instances?maxResults=$(COMPUTE_INSTANCES_MAXRESULTS)&pageToken=$(shell cat json-dumps/compute-instances-$*.json | jq -r '.nextPageToken')' \
		| $(JSON_CLEANER) instances \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-empty.json: json-dumps/compute-instances-$(ZONE_EMPTY).json
	ln -sf $(notdir $<) $@


json-dumps/compute-migs-%.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$*/instanceGroupManagers' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-migs-empty.json: json-dumps/compute-migs-$(ZONE_EMPTY).json
	ln -sf $(notdir $<) $@

json-dumps/compute-disks-%.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones/$*/disks' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-disks-empty.json: json-dumps/compute-disks-$(ZONE_EMPTY).json
	ln -sf $(notdir $<) $@

json-dumps/compute-interconnects.json:
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/interconnects' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-network-%.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/networks/$*' \
		| $(JSON_CLEANER) compute-network \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-sslCertificates.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/sslCertificates/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-forwardingRules.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/forwardingRules/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-forwardingRules-%.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$*/forwardingRules/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-aggregated-forwardingRules.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/aggregated/forwardingRules/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-backendServices.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/backendServices/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-backendServices-%.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$*/backendServices/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-aggregated-backendServices.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/aggregated/backendServices/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-aggregated-targetHttpsProxies.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/aggregated/targetHttpsProxies/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-targetHttpsProxies.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/targetHttpsProxies/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-targetSslProxies.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/targetSslProxies/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-project.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)' \
		| $(JSON_CLEANER) compute-project \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-regions.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-subnetworks-aggregated.json:
	$(CURL) -fsS \
	'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/aggregated/subnetworks' \
	| $(JSON_CLEANER) other \
	| $(SED_SUBST_FAKE) >$@

json-dumps/compute-templates.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/instanceTemplates' \
		| $(JSON_CLEANER) compute-templates \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-zones.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/zones' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-instances-aggregated.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/aggregated/instances' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-igs-aggregated.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/aggregated/instanceGroups' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-migs-aggregated.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/aggregated/instanceGroupManagers' \
		| $(SED_SUBST_FAKE) >$@

# cloudresourcemanager.googleapis.com

json-dumps/iam-policy.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID):getIamPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

json-dumps/org-constraint-%.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v1/projects/$(PROJECT_ID):getEffectiveOrgPolicy' \
		-X POST  --header "Content-Type:text/json" \
		-d "{\"constraint\": \"constraints/$*\"}" \
		| $(JSON_CLEANER) other \
		| $(SED_SUBST_FAKE) >$@

json-dumps/project.json:
	$(CURL) -fsS \
		'https://cloudresourcemanager.googleapis.com/v3/projects/$(PROJECT_ID)' \
		| $(SED_SUBST_FAKE) >$@


# iam.googleapis.com

json-dumps/iam-roles-custom.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/roles?view=FULL&pageSize=500' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/iam-service-accounts.json:
	$(CURL) -fsS \
		'https://iam.googleapis.com/v1/projects/$(PROJECT_ID)/serviceAccounts' \
		| $(JSON_CLEANER) service-accounts \
		| $(SED_SUBST_FAKE) >$@

# serviceusage.googleapis.com

json-dumps/services.json:
	$(CURL) -fsS \
	        'https://serviceusage.googleapis.com/v1/projects/$(PROJECT_ID)/services?filter=state:ENABLED' \
		| $(SED_SUBST_FAKE) >$@
