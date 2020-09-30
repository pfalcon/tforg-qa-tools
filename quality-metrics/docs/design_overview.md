# Multi-tier architecture
The quality-metrics setup is designed based on a multi-tier architecture where we have different components at each tier. Current design has components at 3 tiers:
1. front-end components which include a number of data generator scripts that compute the metric to be tracked and visualised. There is Grafana visualisation component to visualise the quality metrics data.
1. middleware components which include a broker component that acts as an abstraction layer on top of the backend-components. This broker component performs basic data sanity checks and any data translation required.
1. back-end components which include the InfluxDB timeseries database as the data sink.

## Front-end: Data Generator scripts and Grafana visualisation tool
Data generator scripts are metric specific scripts that are expected to be integrated as part of the regular CI setup. Metrics are generated based on a pre-determined frequency with which it is executed in the team's CI setup. Each data generator script is expected to compute the agreed metric and push the metric data along with the associated metadata to the broker component as a JSON data fragment which then gets pushed to the backend for visualisation.

The data generator scripts are organised on a per-team basis.

Grafana tool is used to visualise the quality metrics data on a per-team basis.

### Defect Metric
This metric tracks the open defects against a given project.

### Code Churn Metric
This metric tracks the code churn, that is number of lines added, modified and deleted, against given tag for a project.

### Code Complexity Metric
This metric tracks the code complexity against a given tag for a project. It reports modified McCabe score for the code complexity where a switch-statement is treated as a single decision point, thus reporting a value of 2. It uses pmccabe utility for calculating complexity score, and list all the functions having "Modified McCabe Cyclomatic Complexity" above the agreed upon threshold are pushed to database.

### Other Metrics
While the above mentioned metrics are computed by data generator scripts, there are some other metrics like image size, MISRA defects and run time instrumentation, which are not computed by data generator scripts. The role of scripts present in data generator folder for these metrics is to convert the input text file containing data (to be written to DB) into JSON file (which is sent to broker component). These input text files are expected to be generated as part of CI setup.

## Middleware: Broker component
The broker component provides a level of abstraction and decouples the data generator components from the backend components. This decoupling allows ease of future changes if a new database or visualisation component is to be added, without major changes needed at the front-end scripts.

The broker component provides a simple token-based authentication scheme to validate the data sources that pushes the metrics data to the quality metrics setup. A token is issued on a per-team basis in this setup. The broker component implements a service queue for the data requests received from clients. The broker component always does a sanity check of the data pushed by a client. Only well-formed data against agreed data template will be processed by the broker component. The broker component can perform agreed data transformation also on some data pushed to it before committing them to the backend data base.

## Back-end: InfluxDB database
The backend consists of the data sink component which holds the quality metrics data. An individual data model is defined for each metric. The below sections capture the details of the individual measurements and the InfluxDB line protocol outlining the data model. Separate database is created for each metric for a team and all measurements associated with a metric is held on this database.

### TF-A Defect Data Model
This database holds the measurements which contains data for the open defects against TFA components raised in GitHub.

#### Measurement: TFA_Defects_Tracking
This measurement captures the open defect count against TFA in GitHub and allows to visualize the trend over time.

Line Protocol Description: TFA_Defects_Tracking,Measured_Date=[timestamp in date format]   Issue_Status=[Open from GitHub Issue states],Number_of_Defects=[integer value for the defect count]

#### Measurement: TFA_Defects_Statistics
This measurement is a holding database for the raw data to feed into the TFA_Defects_Tracking.

Line Protocol Description: TFA_Defects_Statistics,Defect_ID=[defect identifier],Measured_Date=[timestamp in date format]   Title=[Defect title],Issue_Status=[Open|Closed|... from GitHub Issue states],URL=[URL to the issue]

### TF-A Code Churn Data Model
This database holds the measurements that is used to provide the visualization for the trend of LoC changes over time against the TFA (trusted-firmware-a) code base.

#### Measurement: TFA_CodeChurn_Tracking
This measurement captures the LoC add/delete/modified count against the TFA versions and allows to visualize the trend over time.

Line Protocol Description: TFA_CodeChurn_Tracking,Git_Tag_Date=[Git Tag Date],Target_Tag=[TFA version tag],Base_Tag=[base tag]     Lines_of_Change=[LoC changed]


### TF-A Complexity Data Model
This database holds the measurements that is used to provide the visualization for the trend of complex functions over time against the TFA code.

#### Measurement: TFA_Complexity_Tracking
This measurement captures the function count which are above a given threshold against the TFA code base and allows to visualize the trend over time.

Line Protocol Description: TFA_Complexity_Tracking,Git_Tag_Date=[Git Tag Date],Target_Tag=[TFA version tag]    Threshold=[threshold value],Whitelisted=[no],Functions_Exceeding_Threshold_Not_Whitelisted=[number of functions exceeding complexity threshold which are not whitelisted]

#### Measurement: TFA_Complexity_Statistics
This measurement is a holding database for the raw data to feed into the TFA_Complexity_Tracking.

Line Protocol Description: TFA_Complexity_Statistics,Git_Tag_Date=[Git Tag Date],Base_Tag=[base tag],Target_Tag=[TFA version tag],Location=[path in the code base for the function]    Function_ID=[function identifier],Score=[mccabe score],Threshold=[threshold value],Whitelisted=[yes|no]

Most data models can also be interpreted from [JSON schemas](../broker-component/metrics-schemas). "data" section contains the details about fields and tags.

## License
[BSD-3-Clause](../../license.md)

