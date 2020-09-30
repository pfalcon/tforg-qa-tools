# Visualisation User Guide
Once broker component is up and running, and it is verified that data is getting pushed to InfluxDB, it can be visualised using Grafana. Following are the steps to create Grafana dashboard:

1. Go to `http://[Host public IP address]:3000` and sign in using the appropriate credentials (Grafana has the following default credentials:  admin, admin).
1. Create data sources for each of the database. Set the value of data source name, database and URL to "`http://[Host public IP address]:8086`". Click on "Save & Test".
1. In order to create dashboard, click on '+' sign on the left side bar. Select "Import" and paste the content of JSON file from [sample dashboards](./sample-dashboards) folder for the dashboard that needs to be created. In [sample dashboards](./sample-dashboards), TFA dashboards JSON files have been provided for reference. User can also create custom dashboard or modify sample ones. For details on creating dashboard, please refer [Grafana Labs](https://grafana.com/docs/grafana/latest/getting-started/getting-started/).

Following table captures the details of datasource for the dashboards provided in [sample dashboards](./sample-dashboards) folder:

|  S. No.  | Data Source Name | Database |
| ------------- | ------------- | ------------- |
| 1  | TFA_CodeChurn  | TFA_CodeChurn |
| 2  | TFA_Complexity  | TFA_Complexity  |
| 3  | TFA_Defects  | TFA_Defects  |
| 4  | TFA_ImageSize  | TFA_ImageSize  |
| 5  | TFA_MisraDefects  | TFA_MisraDefects  |
| 6  | TFA_RunTime_Perf  | TFA_RTINSTR  |

Please note that URL remains same for all the data sources, i.e., `http://[Host public IP address]:8086`
