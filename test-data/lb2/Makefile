PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner

FAKE_PROJECT_ID_SUFFIX = aaaa
FAKE_PROJECT_NR = 12340009
FAKE_ORG_ID = 11112222
SED_SUBST_FAKE = sed -e "s/$(PROJECT_ID_SUFFIX)/$(FAKE_PROJECT_ID_SUFFIX)/" \
				-e "s/$(PROJECT_NR)/$(FAKE_PROJECT_NR)/" \
				-e "s/$(ORG_ID)/$(FAKE_ORG_ID)/" \

REGION1 = europe-west4

ZONE1 = us-east1-b
ZONE2 = europe-west4-b

all:	\
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/compute-igs-$(ZONE1).json \
	json-dumps/compute-instances-$(ZONE1).json \
	json-dumps/compute-instances-$(ZONE2).json \
	json-dumps/compute-negs-$(ZONE2).json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-project.json \
	json-dumps/compute-regions.json \
	json-dumps/compute-zones.json \
	json-dumps/compute-aggregated-backendServices.json \
	json-dumps/compute-backendServices-$(REGION1).json \
	json-dumps/compute-aggregated-forwardingRules.json \
	json-dumps/healthChecks.json \
	json-dumps/regionHealthChecks-$(REGION1).json \
	json-dumps/lb-insights-$(REGION1).json \
	json-dumps/lb-insights-global.json \
	json-dumps/backendService-web-backend-service-get-health-instanceGroups-lb-backend-example-$(ZONE1).json \
	json-dumps/regionBackendService-backend-service-2-$(REGION1)-get-health-networkEndpointGroups-neg1-$(ZONE2).json \
	json-dumps/logging-entries-1.json \
	json-dumps/monitoring-query.json \
	json-dumps/compute-igs-aggregated.json

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

json-dumps/regionHealthChecks-%.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/$*/healthChecks/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/healthChecks.json:
	$(CURL) -fsS \
	        'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/healthChecks/' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/lb-insights-%.json:
	$(CURL) -fv \
	-H "Authorization: Bearer $(gcloud auth print-access-token)" \
	-H "x-goog-user-project: $(PROJECT_ID)" \
	  'https://recommender.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$*/insightTypes/google.networkanalyzer.networkservices.loadBalancerInsight/insights' \
	  | $(SED_SUBST_FAKE) >$@

json-dumps/backendService-web-backend-service-get-health-instanceGroups-lb-backend-example-us-east1-b.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/backendServices/web-backend-service/getHealth' \
		--data '{"group": "projects/$(PROJECT_ID)/zones/$(ZONE)/instanceGroups/lb-backend-example"}' \
		--header "Content-Type:text/json" \
		| $(SED_SUBST_FAKE) >$@


json-dumps/regionBackendService-backend-service-2-europe-west4-get-health-networkEndpointGroups-neg1-europe-west4-b.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/regions/europe-west4/backendServices/backend-service-2/getHealth' \
		--data '{"group": "projects/$(PROJECT_ID)/zones/europe-west4-b/networkEndpointGroups/neg1"}' \
		--header "Content-Type:text/json" \
		| $(SED_SUBST_FAKE) >$@


# If you need to recreate the JSON: adapt the timestamp and make sure that there are some entries found.
define LOGGING_ENTRIES_BODY
{
	"resourceNames": ["projects/$(PROJECT_ID)"],
	"orderBy": "timestamp desc",
	"filter": "
		resource.type=\"gce_instance_group\"
		log_name=\"projects/gcpdiag-lb2-mqc6ejd8/logs/compute.googleapis.com%2Fhealthchecks\"
		resource.labels.instance_group_name=\"lb-backend-example\"
		resource.labels.location=us-east1-b
		jsonPayload.healthCheckProbeResult.healthState=\"UNHEALTHY\"
	"
}
endef
export LOGGING_ENTRIES_BODY

json-dumps/logging-entries-1.json:
	$(CURL) -fsS \
		'https://logging.googleapis.com/v2/entries:list' \
		--header "Content-Type:text/json" \
		-d "$$LOGGING_ENTRIES_BODY" \
		| $(SED_SUBST_FAKE) >$@
