PROJECT_ID  := $(shell terraform output -raw project_id)
PROJECT_ID_SUFFIX := $(shell terraform output -raw project_id_suffix)
PROJECT_NR  := $(shell terraform output -raw project_nr)
ORG_ID      := $(shell terraform output -raw org_id)
CURL         = ../../bin/curl-wrap.sh
JSON_CLEANER = ../../bin/json-cleaner
ZONE_1       = us-central1-a

FAKE_PROJECT_ID_SUFFIX = runbook
FAKE_PROJECT_NR = 12345601
FAKE_ORG_ID = 11112222

COMPUTE_INSTANCES_MAXRESULTS=5

INSTANCE_NAME_GCE1=public-linux-valid
INSTANCE_NAME_GCE2=public-linux-faulty
INSTANCE_NAME_GCE3=private-linux-valid
INSTANCE_NAME_GCE4=private-linux-faulty

GATEWAY_NAME=nat-gateway

CONNECTIVITY_TEST_ID=vmexternalipconnectivitytest

all:	\
	json-dumps/compute-effective-firewalls-default.json \
	json-dumps/compute-instances-$(ZONE_1).json \
	json-dumps/compute-instances-empty.json \
	json-dumps/compute-disks-empty.json \
	json-dumps/compute-network-default.json \
	json-dumps/compute-project.json \
	json-dumps/compute-zones.json \
	json-dumps/iam-policy.json \
	json-dumps/iam-service-accounts.json \
	json-dumps/project.json \
	json-dumps/services.json \
	json-dumps/compute-network-routes.json \
	json-dumps/connectivity-test.json \
	json-dumps/monitoring-query-nat-allocation-failed.json \
	json-dumps/monitoring-query-nat-dropped-sent-packets-count.json \
	json-dumps/monitoring-query-nat-dropped-received-packets-count.json \
	json-dumps/monitoring-query-instance-dropped-received-packets-count.json \




include ../Makefile.inc

define MONITORING_QUERY_NAT_ALLOCATION_FAILED
{ \
  "query": "fetch nat_gateway \
	| metric 'router.googleapis.com/nat/nat_allocation_failed' \
	| within 5m \
	" \
}
endef

json-dumps/monitoring-query-nat-allocation-failed.json:
	$(CURL) -fsS \
		'https://monitoring.googleapis.com/v3/projects/$(PROJECT_ID)/timeSeries:query' \
		--header "Content-Type: application/json" -X POST \
		--data '$(MONITORING_QUERY_NAT_ALLOCATION_FAILED)' \
		| $(SED_SUBST_FAKE) >$@


define MONITORING_QUERY_NAT_DROPPED_SENT_PACKETS_COUNT
{ \
  "query": "fetch nat_gateway \
	| metric 'router.googleapis.com/nat/dropped_sent_packets_count' \
	| align rate(10m) | within 10m \
	| group_by [metric.reason], [value_dropped_sent_packets_count_aggregate:aggregate(value.dropped_sent_packets_count)] \
	" \
}
endef

json-dumps/monitoring-query-nat-dropped-sent-packets-count.json:
	$(CURL) -fsS \
		'https://monitoring.googleapis.com/v3/projects/$(PROJECT_ID)/timeSeries:query' \
		--header "Content-Type: application/json" -X POST \
		--data '$(MONITORING_QUERY_NAT_DROPPED_SENT_PACKETS_COUNT)' \
		| $(SED_SUBST_FAKE) >$@


define MONITORING_QUERY_NAT_DROPPED_RECEIVED_PACKETS_COUNT
{ \
  "query": "fetch nat_gateway \
	| metric 'router.googleapis.com/nat/dropped_received_packets_count' \
	| align rate(5m) | within 5m \
	| group_by [], [value_dropped_received_packets_count_aggregate:aggregate(value.dropped_received_packets_count)] \
	" \
}
endef

json-dumps/monitoring-query-nat-dropped-received-packets-count.json:
	$(CURL) -fsS \
		'https://monitoring.googleapis.com/v3/projects/$(PROJECT_ID)/timeSeries:query' \
		--header "Content-Type: application/json" -X POST \
		--data '$(MONITORING_QUERY_NAT_DROPPED_RECEIVED_PACKETS_COUNT)' \
		| $(SED_SUBST_FAKE) >$@


define MONITORING_QUERY_INSTANCE_DROPPED_RECEIVED_PACKETS_COUNT
{ \
  "query": "fetch gce_instance \
	| metric 'compute.googleapis.com/nat/dropped_received_packets_count' \
	| align rate(5m) | every 5m \
	| group_by [resource.instance_id], [value_dropped_received_packets_count_aggregate:aggregate(value.dropped_received_packets_count)] \
	" \
}
endef

json-dumps/monitoring-query-instance-dropped-received-packets-count.json:
	$(CURL) -fsS \
		'https://monitoring.googleapis.com/v3/projects/$(PROJECT_ID)/timeSeries:query' \
		--header "Content-Type: application/json" -X POST \
		--data '$(MONITORING_QUERY_INSTANCE_DROPPED_RECEIVED_PACKETS_COUNT)' \
		| $(SED_SUBST_FAKE) >$@

json-dumps/connectivity-test.json:
	$(CURL) -fsS \
		'https://networkmanagement.googleapis.com/v1/projects/$(PROJECT_ID)/locations/global/connectivityTests/$(CONNECTIVITY_TEST_ID)' \
		--header "Content-Type:text/json" \
		| $(SED_SUBST_FAKE) >$@

json-dumps/compute-network-routes.json:
	$(CURL) -fsS \
		'https://compute.googleapis.com/compute/v1/projects/$(PROJECT_ID)/global/routes' \
		--header "Content-Type:text/json" \
		| $(SED_SUBST_FAKE) >$@
