PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340010
FAKE_ORG_ID = 22223333
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
				-e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
				-e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

REGION1 = europe-west4
ZONE1 = europe-west4-a
CLOUD_ROUTER = public-nat-cloud-router


all:	\
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/compute-instances-$(ZONE1).json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-network-nat-vpc-network.json \
	json-dumps/monitoring-query.json \
	json-dumps/compute-routers-$(REGION1).json \
	json-dumps/compute-routers-natMappingInfo-$(CLOUD_ROUTER).json \
	json-dumps/compute-routers-routerStatus-$(CLOUD_ROUTER).json \
	json-dumps/compute-routers-natIpInfo-$(CLOUD_ROUTER).json

include ../Makefile.inc

define MONITORING_QUERY_NAT_ALLOCATION_FAILED
{ \
  "query": "fetch nat_gateway \
	| metric 'router.googleapis.com/nat/nat_allocation_failed' \
	| within 5m \
	" \
}
endef

json-dumps/monitoring-query.json:
	$(CURL) -fsS \
		'https://monitoring.googleapis.com/v3/projects/$(PROJECT_ID)/timeSeries:query' \
		--header "Content-Type: application/json" -X POST \
		--data '$(MONITORING_QUERY_NAT_ALLOCATION_FAILED)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-routers-%.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$*/routers/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-routers-natMappingInfo-%.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$(REGION1)/routers/$*/getNatMappingInfo' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-network-nat-vpc-network.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/networks/nat-vpc-network' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-routers-routerStatus-%.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$(REGION1)/routers/$*/getRouterStatus' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-routers-natIpInfo-%.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$(REGION1)/routers/$*/getNatIpInfo' \
		| $(SED_SUBST_FAKE) >$@
