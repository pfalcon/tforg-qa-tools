# quality-metrics

The *quality-metrics* implements a set of components that enable project teams to generate and track code quality metrics for data driven quality improvement. It comprises of:
- a set of data generator scripts that produce quality metrics data (like code churn, open defects, code complexity etc.) for a given project.
- a data broker middleware component to manage the capturing of the data generated by multiple projects.
- a database backend to store and track the generated quality metrics; current implementation uses [InfluxDB](https://github.com/influxdata/influxdb) time-series database.
- a visualisation front-end to view the trend of these metrics over time with [Grafana](https://github.com/grafana/grafana) visualisation tool.
- a set of docker files for easy deployment of containerised components.

Additional documentation is also provided that outlines how a user can visualise InfluxDB data using Grafana.

## Design Overview
Please refer to [design overview](./docs/design_overview.md) for design details for the broker component and the data generator scripts.

## Broker Component User Guide
[Broker component user guide](./docs/broker_component_user_guide.md) contains details of how to bring up the broker component that implements APIs (Application Programming Interface) for data generator clients. The data generator clients POST metrics data, which in-turn gets committed to the backend database. It performs a set of basic sanity check before commiting any metrics data and provides simple token-based authentication for clients.

## Data Generator User Guide
Please refer to [data generator user guide](./docs/data_generator_user_guide.md) for details on how metrics data is generated. These data generator scripts are typically integrated with individual projects CI (Continuous Integration) setup.

## Visualisation User Guide
[Visualisation user guide](./docs/visualisation_user_guide.md) contains details on visualising the InfluxDB data using Grafana.

## License
[BSD-3-Clause](../license.md)