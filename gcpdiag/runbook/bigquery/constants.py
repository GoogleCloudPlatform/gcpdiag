# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Constants for BigQuery runbooks."""
# pylint: disable=unused-wildcard-import, wildcard-import
from typing import Dict, Set, Tuple

from gcpdiag.runbook.gcp.constants import *
from gcpdiag.runbook.iam.constants import *

RUNBOOK_PERMISSION_MAP: Dict[str, Dict[str, Set[str]]] = {
    'Failed Query Runbook': {
        'mandatory_project': {
            'bigquery.jobs.get',
            'bigquery.jobs.create',
            'serviceusage.services.use',
            'serviceusage.services.list',
        },
        'optional_project': {'bigquery.jobs.listAll',},
    },
    'Slow Query First Execution Runbook': {
        'mandatory_project': {'bigquery.jobs.get',},
        'optional_project': {
            'bigquery.jobs.listAll',
            'bigquery.jobs.create',
            'bigquery.jobs.list',
            'bigquery.reservations.list',
            'bigquery.reservationAssignments.list',
        },
        'optional_org': {
            'bigquery.jobs.listAll',
            'bigquery.reservations.list',
            'bigquery.reservationAssignments.list',
        },
    },
    'Slow vs Fast Query Runbook': {
        'mandatory_project': {'bigquery.jobs.get',},
        'optional_project': {
            'bigquery.jobs.listAll',
            'bigquery.jobs.create',
            'bigquery.reservations.list',
            'bigquery.reservationAssignments.list',
        },
        'optional_org': {
            'bigquery.jobs.listAll',
            'bigquery.reservations.list',
            'bigquery.reservationAssignments.list',
        },
    },
}

ERROR_MAP: Dict[
    Tuple,
    Dict[str, str],
] = {
    (
        'Resources exceeded during query execution',
        'Too many DML statements outstanding against',
    ): {
        'cause':
            ('This error occurs when you exceed the limit of 20 DML statements'
             ' in PENDING status in a queue for a single table. This error'
             ' usually occurs when you submit DML jobs against a single table'
             ' faster than what BigQuery can process'),
        'remediation': (
            'One possible solution is to group multiple smaller DML operations'
            ' into larger but fewer jobs—for example, by batching updates and'
            ' inserts. When you group smaller jobs into larger ones, the cost'
            ' to run the larger jobs is amortized and the execution is faster.'
            ' Consolidating DML statements that affect the same data generally'
            ' improves the efficiency of DML jobs and is less likely to exceed'
            ' the queue size quota limit. Avoid DML statements that update or'
            ' insert single rows - batch your updates and inserts. Other'
            ' solutions to improve your DML efficiency could be to partition or'
            ' cluster your tables - see'
            ' https://cloud.google.com/bigquery/docs/data-manipulation-language#best_practices'
            ' for DML best practices.'),
    },
    (
        'UPDATE or DELETE statement over table',
        'would affect rows in the streaming buffer',
    ): {
        'cause':
            ('BigQuery does supported running mutating Data Manipulation'
             ' Language (DML) statements (UPDATE, DELETE, or MERGE) against any'
             ' data recently streamed into BigQuery using the legacy streaming'
             ' API using `tabledata.insertall` within the last 30 minutes.'),
        'remediation':
            ('Consider switching to use the BigQuery Storage Write API where'
             ' this limitations has been lifted.'),
    },
    ('No matching signature',): {
        'cause':
            ('This error is returned if at least one of the arguments passed to'
             ' the function do not match the expected argument type.'),
        'remediation':
            ('Read through the error message details to identify which'
             ' parameter(s) result in a type mismatch and correct the statement'
             ' by providing parameters of the correct type.'),
    },
    ('Could not serialize access to table', 'due to concurrent update'): {
        'cause': (
            'This error can occur when mutating data manipulation language'
            ' (DML) statements that are running concurrently on the same table'
            ' conflict with each other, or when the table is truncated during a'
            ' mutating DML statement. See'
            'https://cloud.google.com/bigquery/docs/data-manipulation-language'
            '#dml_statement_conflicts'
            ' for more details.'),
        'remediation':
            ('Run DML operations that affect a single table such that they do'
             ' not overlap - either space out DML operations or serialize them'
             ' in such a manner that the next DML operation is triggered after'
             ' the previous one has completed. Try to group more changes into a'
             ' single DML statement instead of sending multiple single DML'
             ' statements. Using partitioned tables can also help - if two'
             ' parallel running DMLs modify separate partitions this will not'
             ' lead to a conflict.'),
    },
    (
        'Response',
        'too large',
        'to return',
    ): {
        'cause': (
            'This error occurs when your query results are larger than the'
            ' maximum response size. Some queries execute in multiple stages,'
            ' and this error returns when any stage returns a response size'
            ' that is too large, even if the final result is smaller than the'
            ' maximum. This error commonly returns when queries use an ORDER BY'
            ' clause.'),
        'remediation': (
            'Adding a LIMIT clause can sometimes help, or removing the ORDER BY'
            ' clause. If you want to ensure that large results can return, you'
            ' can set the allowLargeResults property to True and specify a'
            ' destination table - this can be done specifying the'
            ' `--destination_table` flag when using the bq tool or configuring'
            ' Query settings in BigQuery Studio.'),
    },
    ('CPU seconds were used', 'query must use less than'): {
        'cause': (
            'This error occurs when on-demand queries use too much CPU relative'
            ' to the amount of data scanned.'),
        'remediation': (
            'Otimize your query following the steps outlined in the public'
            ' documentation -'
            ' https://cloud.google.com/bigquery/docs/troubleshoot-queries#ts-resources-exceeded.'
            ' Otherwise, switch to a capacity-based pricing model and use'
            ' dedicated slots.'),
    },
    ('Concurrent jobs in the same session are not allowed',): {
        'cause': ('This error can occur when multiple queries are running'
                  ' concurrently in a session, which is not supported.'),
        'remediation':
            ('No concurrent queries are allowed in the same session - queries'
             ' need to be launched in a serialized way.'),
    },
    ('Invalid snapshot time',): {
        'cause':
            ('Scenario 1: This error can occur when trying to query historical'
             ' data that is outside of the time travel window for the'
             ' dataset.\nScenario 2: One of the tables used in the query is'
             ' dropped and re-created after the query starts.'),
        'remediation': (
            'Scenario 1: Change the query to access historical data within the'
            ' dataset\'s time travel window.\nScenario 2: Check to see if there'
            ' is a scheduled query or application that performs this operation'
            ' that ran at the same time as the failed query. If there is, try'
            ' movingthe process that performs the drop and re-create operation'
            ' to run at a time that doesn\'t conflict with queries that read'
            ' that table.'),
    },
    ('The query is too large',): {
        'cause':
            ('You have exceeded the maximum SQL query length. See'
             ' https://cloud.google.com/bigquery/quotas#query_jobs for actual'
             ' limits.'),
        'remediation':
            ('To stay within this limit, consider 1)replacing large arrays or'
             ' lists with query parameters and 2)breaking a long query into'
             ' multiple queries in the session.'),
    },
    ('Transaction is aborted due to concurrent update against table',): {
        'cause': (
            'A transaction with DML statements is attempted against a table'
            ' with an existing transaction performing DML statements that has'
            ' not yet been committed or rolled back. There are two possible'
            ' scenarios: \nScenario 1: A DML operation updated the table after'
            ' the transaction has already started.\nScenario 2: This error is'
            ' can be encountered if a previous transaction encountered an'
            ' error, but there was no exception handler. It is important to'
            ' understand that BigQuery automatically rolls back the transaction'
            ' 24 hours after the transaction started (e.g.the BEGIN TRANSACTION'
            ' statement was executed). This is because a transaction creates a'
            ' session and sessions terminate automatically after 24 hours of'
            ' inactivity'),
        'remediation': (
            'Scenario 1: Make sure that there are no DML operations modifying'
            ' the table when launching the transaction.Scenario 2: Find the'
            ' existing session by following'
            ' https://cloud.google.com/bigquery/docs/sessions-get-ids#list_active_inactive'
            ' and then terminate it by following'
            ' https://cloud.google.com/bigquery/docs/sessions-terminating.\n If'
            ' you confirmed that there were no DML operations modifying the'
            ' table or existing sessions that were not terminated, please'
            ' contact Google Cloud Support.'),
    },
    (
        'Correlated subqueries',
        'that reference other tables are not supported unless they can be ',
        'de-correlated',
    ): {
        'cause': (
            'This error can occur when your query contains a subquery that'
            ' references a column from outside that subquery, called a'
            ' correlation column. The correlated subquery is evaluated using an'
            ' inefficient, nested execution strategy, in which the subquery is'
            ' evaluated for every row from the outer query that produces the'
            ' correlation columns. Sometimes, BigQuery can internally rewrite'
            ' queries with correlated subqueries so that they execute more'
            ' efficiently. The correlated subqueries error occurs when BigQuery'
            ' can\'t sufficiently optimize the query.'),
        'remediation': (
            'To address this error, try the following:\n1. Remove any ORDER BY,'
            ' LIMIT, EXISTS, NOT EXISTS, or IN clauses from your subquery. \n2.'
            ' Use a multi-statement query to create a temporary table to'
            ' reference in your subquery. \n3. Rewrite your query to use a'
            ' CROSS JOIN instead.'),
    },
    (
        'Requires raw access permissions',
        'on the read columns',
        'to execute the DML statements',
    ): {
        'cause':
            ('This error occurs when you attempt a DML DELETE, UPDATE, or MERGE'
             ' statement, without having the Fine-Grained Reader permission on'
             ' the scanned columns that use column-level access control to'
             ' restrict access at the column level.'),
        'remediation': (
            'Grant the Fine-Grained Reader permission to the user running the'
            ' job. See'
            ' https://cloud.google.com/bigquery/docs/column-level-security-writes'
            ' for more details.'),
    },
    (
        'Cannot parse regular expression',
        'invalid perl operator',
    ): {
        'cause': (
            'BigQuery uses the re2 library for regular expression handling.'
            ' Certain operators are not supported by the re2 library. \nUsers'
            ' might encounter this as a transient problem - it\'s possible that'
            ' the regular expression matching operation in the WHERE clause was'
            ' discarded by a previous condition check and was not evaluated at'
            ' all at runtime.'),
        'remediation':
            ('Study https://github.com/google/re2/wiki/Syntax to identify the'
             ' unsupported regular expression operator and modify your regular'
             ' expression accordingly.'),
    },
    (
        'exceeded the maximum disk and memory limit',
        'available for shuffle operations',
    ): {
        'cause':
            ('This error occurs when a query can\'t access sufficient shuffle'
             ' resources - there is more data that needs to get written to'
             ' shuffle than there available shuffle capacity.'),
        'remediation': (
            'There are three possible solutions to this issue: provisioning more'
            ' resources, reducing the amount of data processed by the'
            ' query or reducing concurrency of queries or materializing intermediate results to '
            'reduce dependence on resources.\n1. Provisioning more resources: If you are using'
            ' on-demand pricing, consider switching to capacity-based analysis'
            ' pricing by purchasing reservations. Reservations give you'
            ' dedicated slots and shuffle capacity for your projects\' queries.'
            ' If you are using BigQuery reservations, slots come with dedicated'
            ' shuffle capacity. Queries running in parallel will share the same'
            ' shuffle capacity. You can try:\n a) Adding more slots to that'
            ' reservation.\n b) Using a different reservation that has more'
            ' slots.\n c) Spread out shuffle-intensive queries, either over'
            ' time within a reservation or over different'
            ' reservations.\n2. Reducing the amount of data processed: Follow'
            ' the recommendations from '
            'https://cloud.google.com/bigquery/docs/best-practices-performance-compute'
            '#reduce-data-processed.'
            ' Certain operations in SQL tend to make more extensive usage of'
            ' shuffle, particularly JOIN operations and GROUP BY clauses. Where'
            ' possible, reducing the amount of data in these operations might'
            ' reduce shuffle usage.\n3. Reduce concurrency of queries or materializing'
            ' intermediate results to reduce dependence on resources.'),
    },
    (
        'Cannot return an invalid timestamp value',
        'relative to the Unix epoch',
    ): {
        'cause':
            ('You are trying to load invalid Unix epoch timestamp values into a'
             ' BigQuery table or you are trying to query a table that contains'
             ' invalid Unix epoch timestamp values.'),
        'remediation': (
            'For loading: Make sure you are providing valid Unix epoch'
            ' timestamp values when loading. \n For querying: For every field'
            ' which has one or more invalid values update them to NULL or valid'
            ' Unix epoch timestamp values using a DML UPDATE statement.'),
    },
    (
        'Resource exhausted',
        'The model might be too large.',
    ): {
        'cause': (
            'Common causes of this issue include and are not limited to: too'
            ' many categorical values in columns; too many features; complex'
            ' architecture of the model (i.e. the number and depth of trees, or'
            ' hidden units in neural nets).'),
        'remediation':
            ('1. Reduce the complexity of the model. \n2. Please contact '
             'bqml-feedback@google.com if you keep running into this issue and '
             'would like to apply for more quota.'),
    },
    (
        'Not enough resources for query planning',
        'too many subqueries',
        'query is too complex',
    ): {
        'cause':
            ('This error occurs when a query is too complex. The primary causes'
             ' of complexity are:\n - WITH clauses that are deeply nested or'
             ' used repeatedly.\n - Views that are deeply nested or used'
             ' repeatedly.\n - Repeated use of the UNION ALL operator.'),
        'remediation': (
            'Try the following:\n - Split the query into multiple queries, then'
            ' use procedural language to run those queries in a sequence with'
            ' shared state.\n - Use temporary tables instead of WITH clauses.\n'
            ' - Rewrite your query to reduce the number of referenced objects'
            ' and comparisons.'),
    },
    (
        'exceeded limit for metric',
        'cloudkms.googleapis.com/hsm_symmetric_requests',
    ): {
        'cause': (
            'The HSM symmetric cryptographic requests per region quota is being'
            ' exceeded.'),
        'remediation': (
            'There are to possible remediations: \n1. Reduce the rate at which'
            ' your '
            'projects are making requests that use Cloud KMS resources. \n2.'
            ' Request '
            'a quota increase for HSM symmetric cryptographic requests per'
            ' region by '
            'following '
            'https://cloud.google.com/kms/docs/monitor-adjust-quotas#increase_quotas.'
        ),
    },
    (
        'Apache Avro',
        'failed',
        'read',
        'Cannot skip stream',
    ): {
        'cause':
            ('This error can occur when loading multiple Avro files with'
             ' different schemas, resulting in a schema resolution issue and'
             ' causing the import job to fail at a random file.'),
        'remediation':
            ('To address this error, ensure that the last alphabetical file in'
             ' the load job contains the superset (union) of the differing'
             ' schemas. This is a requirement based on how Avro handles schema'
             ' resolution. See'
             ' https://avro.apache.org/docs/1.8.1/spec.html#Schema+Resolution.'
            ),
    },
    ('Already Exists: Job',): {
        'cause':
            ('You are trying to create a job with a job id that already exists.'
            ),
        'remediation':
            ('Allow BigQuery to generate a random jobId value instead of'
             ' specifying one explicitly.'),
    },
    (
        'Dataset',
        'was not found in location',
    ): {
        'cause': (
            'This error returns when you refer to a dataset resource that'
            ' doesn\'t exist,or when the location in the request does not match'
            ' the location of the dataset.'),
        'remediation':
            ('To address this issue, specify the location of the dataset in the'
             ' query or confirm that the dataset exists in the mentioned'
             ' location and the identifier is correctly specified.'),
    },
    (
        'Operation timed out',
        'after 6.0 hours',
        'reducing the amount of work',
        'limit.',
    ): {
        'cause': (
            'BigQuery query jobs have an execution time limit of 6 hours, which'
            ' is a system limit that cannot be changed.'),
        'remediation': (
            'If this is the first time you are executing the query, look into'
            ' optimizing query performance by studying the following public'
            ' documentation section:'
            ' https://cloud.google.com/bigquery/docs/best-practices-performance-overview.'
            '\nHowever, if this is a job that previously succeeded much faster, you'
            ' should look into troubleshooting this as a slow query. Currently'
            ' there is a troubleshootiong article available in the public'
            ' documentation -'
            'https://cloud.google.com/bigquery/docs/troubleshoot-queries#troubleshoot_slow_queries'
            ' .Also consider investigating if there was a shortage of available'
            ' slot resources due to a possible increase in the number of'
            ' concurrent queries. See'
            'https://cloud.google.com/bigquery/docs/information-schema-jobs'
            '#view_average_concurrent_jobs_running_alongside_a_particular_job_in_the_same_project'
            ' for an example query.'),
    },
    (
        'Resources exceeded during query execution',
        'executed in the allotted memory',
        ('Top memory consumer(s): sort operation used for table update'
         ' (UPDATE/DELETE/MERGE)'),
    ): {
        'cause':
            ('This can happen when a table has reasonably wide rows and those'
             ' rows need to be updated to a much larger value in size, e.g. 20x'
             ' times the original row size. If there is a large number of rows'
             ' that need to be updated, this can also lead to the encountered'
             ' error.'),
        'remediation':
            (' - Split the UPDATE/MERGE to update less rows at once.\n - Update'
             ' row size less aggressively. For example, split one MERGE'
             ' statement into a few MERGE statements updating a smaller number'
             ' of columns at once so that row size is increased gradually.'),
    },
    (
        'Resources exceeded during query execution',
        'executed in the allotted memory',
        'Out of stack space',
        'deeply nested query expression',
        'query resolution',
    ): {
        'cause': (
            'Query contains too many nested function calls. Sometimes, parts of'
            ' a query are translated to function calls during parsing. For'
            ' example, an expression with repeated concatenation operators,'
            ' such as A || B || C || ..., becomes CONCAT(A, CONCAT(B, CONCAT(C,'
            ' ...))).'),
        'remediation': 'Rewrite your query to reduce the amount of nesting.',
    },
    (
        'Resources exceeded during query execution',
        'executed in the allotted memory',
        'Top memory consumer(s): query parsing and optimization',
    ): {
        'cause': (
            'The issue is caused by the complexity of the query statement (i.e.'
            ' number if columns, statements, literals, etc.).'),
        'remediation':
            (' - Split the query into smaller queries containing fewer'
             ' literals.\n - Materialize inner query results to use them in'
             ' another SELECT statement.'),
    },
    (
        'Resources exceeded during query execution',
        'executed in the allotted memory',
        'ORDER BY',
    ): {
        'cause':
            ('An ORDER BY operation is quite expensive and cannot be processed'
             ' in parallel - sorting will happen on asingle compute unit, which'
             ' can run out of memory if it needs to process too many rows.'),
        'remediation': (' - Use a LIMIT clause to reduce the result set.'
                        '\n - Use additional filters to reduce the result set.'
                        '\n - Remove the ORDER BY clause from the query.'),
    },
    (
        'Resources exceeded during query execution',
        'executed in the allotted memory',
    ): {
        'cause':
            ('For SELECT statements, this error occurs when the query uses too'
             ' many resources.'),
        'remediation': (
            ' - Try removing an ORDER BY clause.\n - If your query uses JOIN,'
            ' ensure that the larger table is on the left side of the clause.'
            ' Also ensure that your data does not contain duplicate join'
            ' keys.\n - If your query uses FLATTEN, determine if it\'s necessary'
            ' for your use case. For more information, see'
            ' https://cloud.google.com/bigquery/docs/data#nested.\n - If your'
            ' query uses EXACT_COUNT_DISTINCT, consider using COUNT(DISTINCT)'
            ' instead.\n - If your query uses COUNT(DISTINCT <value>, <n>) with'
            ' a large <n> value, consider using GROUP BY instead. For more'
            ' information, see'
            ' https://cloud.google.com/bigquery/query-reference#countdistinct.\n'
            ' - If your query uses UNIQUE, consider using GROUP BY instead, or'
            ' a window function inside of a subselect.\n - If your query'
            ' materializes many rows using a LIMIT clause, consider filtering'
            ' on another column, for example ROW_NUMBER(), or removing the'
            ' LIMIT clause altogether to allow write parallelization.\n - If'
            ' your query used deeply nested views and a WITH clause, this can'
            ' cause an exponential growth in complexity, thereby reaching the'
            ' limits.\n - Use temporary tables to store intermediate results'
            ' instead of using WITH clauses. WITH clauses might have to be'
            ' recalculated several times, which can make the query complex and'
            ' therefore slow.\n - Avoid using UNION ALL queries. \n\nSee'
            ' https://cloud.google.com/bigquery/docs/troubleshoot-queries#ts-resources-exceeded'
            ' for more details.'),
    },
    (
        'project',
        'region',
        'exceeded quota',
        'jobs that can be queued per project',
    ): {
        'cause': (
            'You are attempting to queue more interactive or batch queries than'
            ' the queue limit allows. '),
        'remediation': (
            'You can queue up to 1000 interactive and 20000 batch jobs per'
            ' project. This is a hard limit and cannot be raised. Possible'
            ' remediations:\n - Pause the job. If you identify a process or'
            ' pipeline responsible for an increase in queries, then pause that'
            ' process or pipeline.\n - Use jobs with batch priority. You can'
            ' queue more batch queries than interactive queries.\n - Distribute'
            ' queries. Organize and distribute the load across different'
            ' projects as informed by the nature of your queries and your'
            ' business needs.\n - Distribute run times. Distribute the load'
            ' across a larger time frame. If your reporting solution needs to'
            ' run many queries, try to introduce some randomness for when'
            ' queries start. For example, don\'t start all reports at the same'
            ' time.\n - Use BigQuery BI Engine. If you have encountered this'
            ' error while using a business intelligence (BI) tool to create'
            ' dashboards that query data in BigQuery,then we recommend that you'
            ' can use BigQuery BI Engine. Using BigQuery BI Engine is optimal'
            ' for this use case.\n - Optimize queries and data model.'
            ' Oftentimes, a query can be rewritten so that it runs more'
            ' efficiently. For example, if your query contains a Common table'
            ' expression (CTE)–WITH clause–which is referenced in more than one'
            ' place in the query, then this computation is done multiple times.'
            ' It is better to persist calculations done by the CTE in a'
            ' temporary table, and then reference it in the query.\n - Multiple'
            ' joins can also be the source of lack of efficiency. In this case,'
            ' you might want to consider using nested and repeated columns.'
            ' Using this often improves locality of the data, eliminates the'
            ' need for some joins, and overall reduces resource consumption and'
            ' the query run time.\n - Optimizing queries make them cheaper, so'
            ' when you use capacity-based pricing, you can run more queries'
            ' with your slots. For more information, see '
            'https://cloud.google.com/bigquery/docs/best-practices-performance-overview.'
            ' \n - Optimize query model. BigQuery'
            ' is not a relational database. It is not optimized for an infinite'
            'number of small queries. Running a large number of small queries\''
            ' quickly depletes your quotas. Such queries don\'t run as'
            ' efficiently as they do with the smaller database products.'
            ' BigQuery is a large data warehouse and this is its primary use'
            ' case. It performs best with analytical queries over large amounts'
            ' of data.\n - Persist data (Saved tables). Pre-process the data in'
            ' BigQuery and store it in additional tables. For example, if you'
            ' execute many similar, computationally-intensive queries with'
            ' different WHERE conditions, then their results are not cached.'
            ' Such queries also consume resources each time they run. You can'
            ' improve the performance of such queries and decrease their'
            ' processing time by pre-computing the data and storing it in a'
            ' table. This pre-computed data in the table can be queried by'
            ' SELECT queries. It can often be done during ingestion within the'
            ' ETL process, or by using scheduled queries or materialized'
            ' views.\n - Use dry run mode. Run queries in dry run mode, which'
            ' estimates the number of bytes read but does not actually process'
            ' the query.\n - Preview table data. To experiment with or explore'
            ' data rather than running queries, preview table data with'
            ' BigQuery\'s table preview capability.\n - Use cached query'
            ' results. All query results, including both interactive and batch'
            ' queries, are cached in temporary tables for approximately 24'
            ' hours with some exceptions. While running a cached query does'
            ' still count against your concurrent query limit, queries that use'
            ' cached results are significantly faster than queries that don\'t'
            ' use cached results because BigQuery does not need to compute the'
            ' result set.'),
    },
    (
        'Quota exceeded',
        'table exceeded quota',
        'Number of partition modifications',
        'column partitioned table',
    ): {
        'cause': '',
        'remediation':
            'This quota cannot be increased. To mitigate, do the following:'
            '\n - Change the partitioning on the table to have more data in each partition, '
            'in order to decrease the total number of partitions. For example, change from '
            'partitioning by day to partitioning by month or change how you partition the table.'
            '\n - Use clustering instead of partitioning.'
            '\n - If you frequently load data from multiple small files stored in Cloud Storage '
            'that uses a job per file, then combine multiple load jobs into a single job. You can'
            ' load from multiple Cloud Storage URIs with a comma-separated list (for example, '
            'gs://my_path/file_1,gs://my_path/file_2), or by using wildcards (for example, '
            'gs://my_path/*).'
            '\n - If you use load, select or copy jobs to append single rows of data to a table, '
            'for example, then you should consider batching multiple jobs into one job. BigQuery '
            'doesn\'t perform well when used as a relational database. As a best practice, avoid '
            'running frequent, single-row append actions.'
            '\n - To append data at a high rate, consider using BigQuery Storage Write API. It is'
            'a recommended solution for high-performance data ingestion. The BigQuery Storage '
            'Write API has robust features, including exactly-once delivery semantics.'
            'To monitor the number of modified partitions on a table, use the INFORMATION_SCHEMA '
            'view.'
    },
    (
        'Input',
        'CSV files are not splittable',
        'files is larger',
        'maximum allowed size',
    ): {
        'cause':
            'If you load a large CSV file using the bq load command with the '
            '--allow_quoted_newlines flag, you might encounter this error.',
        'remediation':
            '1. Set the --allow_quoted_newlines flag to false. \n2. Split the CSV '
            'file into smaller chunks that are each less than 4 GB.'
    },
    (
        'table',
        'exceeded',
        'imports or query appends per table',
    ): {
        'cause':
            'BigQuery returns this error message when your table reaches the limit '
            'for table operations per day for Standard tables. Table operations include the '
            'combined total of all load jobs, copy jobs, and query jobs that append or overwrite '
            'a destination table. The limit can be found here: '
            'https://cloud.google.com/bigquery/quotas#standard_tables .',
        'remediation':
            'This quota cannot be increased. To remediate, do the following:'
            '\n - If you frequently load data from multiple small files stored in Cloud Storage '
            'that uses a job per file, then combine multiple load jobs into a single job. You '
            'can load from multiple Cloud Storage URIs with a comma-separated list (for example, '
            'gs://my_path/file_1,gs://my_path/file_2), or by using wildcards (for example, '
            'gs://my_path/*).'
            '\n - If you use load, select or copy jobs to append single rows of data to a table, '
            'for example, then you should consider batching multiple jobs into one job. BigQuery '
            'doesn\'t perform well when used as a relational database. As a best practice, avoid '
            'running frequent, single-row append actions.'
            '\n - To append data at a high rate, consider using BigQuery Storage Write API. It is'
            ' a recommended solution for high-performance data ingestion. The BigQuery Storage '
            'Write API has robust features, including exactly-once delivery semantics.'
            '\n - To monitor the number of modified partitions on a table, use the '
            'INFORMATION_SCHEMA view.'
    },
    (
        'Exceeded rate limits',
        'too many table update operations',
    ): {
        'cause':
            'The table reached the limit for maximum rate of table metadata update '
            'operations per table for Standard tables. Table operations include the combined '
            'total of all load jobs, copy jobs, and query jobs that append to or overwrite a '
            'destination table. API calls like PatchTable, UpdateTable or '
            'InsertTable also count as table metadata update operations. To diagnose where the '
            'operations are coming from, follow the steps in '
            'https://cloud.google.com/bigquery/docs/troubleshoot-quotas'
            '#ts-maximum-update-table-metadata-limit-diagnose.',
        'remediation':
            ' - Reduce the update rate for the table metadata.'
            '\n - Add a delay between jobs or table operations to make sure that the update '
            'rate is within the limit.'
            '\n - For data inserts or modification, consider using DML operations. DML operations'
            ' are not affected by the Maximum rate of table metadata update operations per table '
            'rate limit (DML operations have their own limits).'
            '\n - If you frequently load data from multiple small files stored in Cloud Storage '
            'that uses a job per file, then combine multiple load jobs into a single job. You can'
            ' load from multiple Cloud Storage URIs with a comma-separated list (for example, '
            'gs://my_path/file_1,gs://my_path/file_2), or by using wildcards (for example, '
            'gs://my_path/*).'
            '\n - If you use load, select or copy jobs to append single rows of data to a table, '
            'for example, then you should consider batching multiple jobs into one job. BigQuery '
            'doesn\'t perform well when used as a relational database. As a best practice, avoid '
            'running frequent, single-row append actions.'
            '\n - To append data at a high rate, consider using BigQuery Storage Write API. It '
            'is a recommended solution for high-performance data ingestion. The BigQuery Storage '
            'Write API has robust features, including exactly-once delivery semantics.'
    },
    (
        'project',
        'exceeded quota for free query bytes scanned',
    ): {
        'cause':
            'BigQuery returns this error when you run a query in the free usage tier '
            'and the account reaches the monthly limit of data size that can be queried without '
            'a paid Cloud Billing account.',
        'remediation':
            'To continue using BigQuery, you need to upgrade the account to a '
            'paid Cloud Billing account.'
    },
    ('exceeded quota for copies per project',): {
        'cause':
            'Your project has exceeded the daily limit for table copy jobs. See the '
            'limit here: https://cloud.google.com/bigquery/quotas#copy_jobs.',
        'remediation':
            'Wait for the daily quota to be replenished.'
            '\nIf the goal of the frequent copy operations is to create a snapshot '
            'of data, consider using table snapshots instead. Table snapshots are cheaper and '
            'faster alternative to copying full tables.'
            '\nYou can request a quota increase by contacting support or sales if you need a '
            'bigger quota. It might take several days to review and process the request. We '
            'recommend stating the priority, use case, and the project ID in the request.'
    },
    (
        'exceeded quota',
        'ExtractBytesPerDay',
    ): {
        'cause':
            'The export exceeds the default 50 TiB (Tebibytes) daily limit in a project',
        'remediation':
            'To export more than 50 TiB(Tebibytes) of data per day, do one of '
            'the following: '
            '\n - Create a slot reservation or use an existing reservation and assign your '
            'project into the reservation with job type PIPELINE. You will be billed using '
            'capacity-based pricing.'
            '\n - Use the EXPORT DATA SQL statement. You will be billed using either on-demand '
            'or capacity-based pricing, depending on how the project query pricing is configured.'
            '\n - Use the Storage Read API. You will be billed using the price for streaming '
            'reads. The expiration time is guaranteed to be at least 6 hours from session '
            'creation time.'
    },
    ('too many concurrent queries with remote functions',): {
        'cause':
            'The number of concurrent queries that contain remote functions exceeds the '
            'limit.',
        'remediation':
            'Follow the best practices for using remote functions outlined here:'
            'https://cloud.google.com/bigquery/docs/remote-functions'
            '#best_practices_for_remote_functions.'
            '\nYou can request a quota increase by contacting support or sales if you need a '
            'bigger quota.'
    },
    ('exceeded quota for CREATE MODEL queries per project',): {
        'cause': 'You have exceeded the quota for CREATE MODEL statements.',
        'remediation':
            'If you exceed the quota for CREATE MODEL statements, send an email '
            'to bqml-feedback@google.com and request a quota increase through sales or support.'
    },
    (
        'UPDATE/MERGE',
        'match',
        'one source row for each target row',
    ): {
        'cause':
            'This error will be raised if the table contains duplicated rows. Multiple rows '
            'in the source table match a single row in the target table.',
        'remediation': 'Remove duplicate rows from the table.',
    },
    ('Not found: Table',): {
        'cause': (
            'The query references a table that does not exist or could not be located in '
            'the specified region and project.'),
        'remediation': (
            'Make sure the table exists in the specified dataset and the table '
            'identifier provided is correct.\nAfter that confirm that the query is '
            'executed in the correct region (where the dataset is located).'),
    },
    ('Not found: View',): {
        'cause': (
            'The query references a view that does not exist or could not be located in '
            'the specified region and project.'),
        'remediation': (
            'Make sure the view exists in the specified dataset and the view '
            'identifier provided is correct.\nAfter that confirm that the query is '
            'executed in the correct region (where the dataset is located).'),
    },
    ('Syntax Error',): {
        'cause':
            'This is a user side SQL statement issue.',
        'remediation':
            ('Check your query for syntax errors for the methods or variables'
             ' mentioned in the error message at the specified location.'),
    },
    ('User requested cancellation',): {
        'cause': ('The job was manually stopped by a user request before it'
                  ' couldcomplete or the userconfigured job timeout.'),
        'remediation': (
            'The job did not fail - a user sent a cancel request to stop the'
            ' execution of this job. You can inspect Cloud Logging and look for'
            ' a jobs.cancel request to understand who initiated the'
            ' cancellation.'),
    },
    (
        'Job execution was cancelled',
        'Job timed out after',
    ): {
        'cause': (
            'The job timed out before it could complete. This can happen when a'
            ' job execution reaches an exiting BigQuery limit or when a'
            ' user-defined timeout value is set in the job configuration.'),
        'remediation': (
            'Inspect the job configuration to understand if a timeout value was'
            ' set. If no custom timeout was set, this means that one of the'
            ' execution limits has been reached. See'
            ' https://cloud.google.com/bigquery/quotas for more information'
            ' about execution time limits. Follow'
            ' https://cloud.google.com/bigquery/docs/best-practices-performance-overview'
            ' to optimize query performance. Also consider investigating if'
            ' there was a shortage of available slot resources due to a'
            ' possible increase in the number of concurrent queries. See'
            ' https://cloud.google.com/bigquery/docs/information-schema-jobs'
            '#view_average_concurrent_jobs_running_alongside_a_particular_job_in_the_same_project'
            ' for an example query to get concurrency information.'),
    },
    ('exceeded rate limits',): {
        'cause': (
            'Too many requests have been made in a short period, triggering a rate limit to '
            'protect the service.'),
        'remediation': (
            'Retry the operation after few seconds. Use exponential backoff between '
            'retry attempts. That is, exponentially increase the delay between each retry.'
        ),
    },
    (
        'User does not have',
        'permission in project',
    ): {
        'cause':
            'User does not have sufficient permissions in the mentioned project.',
        'remediation': (
            'Read the error message carefully and grant the permission specified in '
            'the error message to the user who attempted to run the job'),
    },
    ('User does not have permission to query table or perhaps it does not exist',): {
        'cause':
            'There are two possible root causes: the user either does not have the necessary '
            'permissions to look up tables in the project, or the tables does not exist.',
        'remediation': (
            'Follow the troubleshooting advice documented here: '
            'https://cloud.google.com/bigquery/docs/troubleshoot-queries#user_perm'
        ),
    },
    ('csv processing encountered too many errors', 'while parsing'): {
        'cause':
            'There was an issue processing the CSV file(s) submitted by the user in the load job.',
        'remediation': (
            'Carefully read through the error messages above to understand the specific '
            'problem(s) with the file(s). Visit '
            'https://cloud.google.com/bigquery/docs/loading-data-cloud-storage-csv'
            '#troubleshoot_parsing_errors'
            ' for guidance on how to resolve parsing errors.'),
    },
    ('csv processing encountered too many errors',): {
        'cause':
            'There was an issue processing the CSV file(s) submitted by the user in the load job.',
        'remediation': (
            'There are two possible remediations:\n'
            '1. Use --max_bad_records to instruct BigQuery to skip a defined number of rows that '
            'cannot be parsed and let the job complete.\n'
            '2. Fix the file(s) by editing the rows causing the failures and retry the job.\n'
            'If there are additional error messages, they will be printed as well to provide the '
            'location(s) of the problematic row(s).'),
    },
    ('error while reading data', 'error message', 'unable to parse'): {
        'cause':
            'There was an issue reading the mentioned file.',
        'remediation': (
            'The error message above specifies the problem that was encountered, mentions the '
            'problematic file and the position in the file at which the error occurred. Fix the '
            'issue with the file and retry the job. Visit '
            'https://cloud.google.com/bigquery/docs/loading-data-cloud-storage-csv'
            '#troubleshoot_parsing_errors'
            ' for guidance on how to resolve parsing errors.'),
    },
    (
        'error while reading data',
        'error message',
    ): {
        'cause':
            'There was an issue reading the mentioned file.',
        'remediation': (
            'The error message above specifies the problem that was encountered, mentions the '
            'problematic file and the position in the file at which the error occurred. Fix the '
            'issue with the file and retry the job.'),
    },
    (
        'internal error',
        'retry',
    ): {
        'cause':
            'This error usually means that the job failed due to an intermittent issue on '
            'the BigQuery service side. The client has no way to fix or control these errors - '
            'it is only possible to mitigate them by retrying the job.',
        'remediation': (
            ' The main recommendation is to retry the job using truncated exponential '
            'backoffs. For more information about exponential backoffs, see '
            'https://en.wikipedia.org/wiki/Exponential_backoff. \nIf the retries are '
            'not effective and the issues persist, you can calculate the rate of '
            'failing requests by following this article - '
            'https://cloud.google.com/bigquery/docs/error-messages'
            '#calculate-rate-of-failing-requests-and-uptime'
            ' - and contact support with the rate of failing requests.'
            '\nAlso, if you observe a specific job persistently fail with this '
            'internal error, even when retried using exponential backoff on '
            'multiple workflow restart attempts, you should escalate this to '
            'Cloud Support to troubleshoot the issue from the BigQuery side,'),
    },
}
