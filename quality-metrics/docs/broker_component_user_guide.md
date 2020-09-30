# Broker Component User Guide
Broker component is Python Flask app, which handles the data being pushed by the data generator components of the quality metrics project. It implements APIs that allow the data generator scripts to POST metrics data in an agreed JSON format which gets pushed to InfluxDB backend database. For each received request with valid authorization token, it performs basic sanity check and pushes the data to InfluxDB. For details on how to visualize InfluxDB data using Grafana, please refer [visualisation user guide](./visualisation_user_guide.md).

## Deploying broker component
The broker component can be deployed in the infrastructure as a docker container with the docker files in the project.

### Dependencies
- docker
- docker-compose
- python3-dev
- python3-pip
- Ensure that ports 3000, 5000 and 8086 are enabled for incoming traffic.

###  Bringing-up Broker Component - Setup Instructions
In order to bring-up broker component (for a first time setup), docker-compose.yml is used, which brings up 3 containers - Grafana, InfluxDB and Flask App. It is upto the user to adapt the docker_compose.yml file if only some of the components needs to be deployed.
JWT Authorization Token is generated using following steps, which needs to be added in [tfa_variables.sh](../data_generator/tfa_variables.sh)
1. Set value of HOST to host public IP address in file [constants.py](../broker-component/constants.py)
1. [credentials.py](../broker-component/credentials.py) is provided for reference purpose only. Please change the value of SECRET_KEY and password for _tfa_metrics_ user.
1. Ensure the current working directory is broker_component. Create [teamname]_credentials.json (as an example let us use 'tfa' as the teamname) and run following commands to generate Authorization Token:
```bash
$ cat tfa_credentials.json
{
    "username": "tfa_metrics",
    "password": "[tfa_metrics password matching with password in credentials.py]"
}

$ docker network create metrics_network
$ docker volume create influxdb-volume
$ docker volume create grafana-volume
$ docker-compose build
$ docker-compose up -d
$ curl -H "Content-Type: application/json" -X POST -d "$(cat tfa_credentials.json)" http://[Host Public IP]:5000/auth
```

## Testing the setup after deployment
The following steps can help confirm if the deployment steps detailed in previous setup was indeed successful or not.

### Verify that Grafana is up
If URL *http://`[HOST Public IP]`:3000* is accessible, it confirms that Grafana is up.

### Verify that InfluxDB is up
If URL *http://`[HOST Public IP]`:8086/query* is accessible, it confirms that InfluxDB is up.

### Create InfluxDB Database
Database can be created by accessing InfluxDB container or by using InfluxDB API.

#### Create database by accessing InfluxDB container
```bash
$ docker exec -it influxdb_container sh
# influx
> create database TFA_CodeChurn
> create database TFA_Complexity
> create database TFA_Defects
> create database TFA_MisraDefects
> create database TFA_ImageSize
> create database TFA_RTINSTR
> exit
# exit
```
#### Create database using the InfluxDB API
```bash
$ curl -i -XPOST  http://[HOST Public IP]:8086/query --data-urlencode "q=CREATE DATABASE TFA_CodeChurn"
$ curl -i -XPOST  http://[HOST Public IP]:8086/query --data-urlencode "q=CREATE DATABASE TFA_Complexity"
$ curl -i -XPOST  http://[HOST Public IP]:8086/query --data-urlencode "q=CREATE DATABASE TFA_Defects"
$ curl -i -XPOST  http://[HOST Public IP]:8086/query --data-urlencode "q=CREATE DATABASE TFA_MisraDefects"
$ curl -i -XPOST  http://[HOST Public IP]:8086/query --data-urlencode "q=CREATE DATABASE TFA_ImageSize"
$ curl -i -XPOST  http://[HOST Public IP]:8086/query --data-urlencode "q=CREATE DATABASE TFA_RTINSTR"
$ curl -i -XPOST  http://[HOST Public IP]:8086/query --data-urlencode "q=SHOW DATABASES"
```

### Pushing Data to InfluxDB
Data can be pushed to InfluxDB by sending cURL POST request in the agreed-upon format and with correct authorization token.
* The steps above mention that how authorization token can be generated.
* Request is validated using [JSON schemas](../broker-component/metrics-schemas)
In order to send push data, run following commands:
```bash
$ cd qa-tools/quality-metrics/data-generator/tfa_metrics
$ ./tfa_quality_metrics.sh --tag [Release Tag]
```

For details, please refer [data generator user guide](./data_generator_user_guide.md).

## License
[BSD-3-Clause](../../license.md)
