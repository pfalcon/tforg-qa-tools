#!/usr/bin/env bash

#======================================================================
# Copyright (c) 2020, Arm Limited. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
#======================================================================

export TFA_REPO='https://github.com/ARM-software/arm-trusted-firmware.git'
export GITHUBPY_REPO='https://github.com/michaelliao/githubpy.git'

export DEFECT_LOG=tfa_defects_summary.txt
export COMPLEXITY_LOG=tfa_complexity_summary.txt
export CODE_CHURN_LOG=tfa_code_churn.txt

# Authentication token needs to be generated using following command:
# curl -H "Content-Type: application/json" -X POST -d \
# "$(cat <CREDENTIALS_JSON_FILE>)" http://<IP_ADDR>:5000/auth
# where "IP_ADDR" is the IP address of host where metrics server is running, and
# CREDENTIALS_JSON file should contain credentials which should match with
# the credentials in ../../broker-component/credentials.py
# Response would contain a JWT token, which needs to be added here
# during deployment
export TFA_METRICS_AUTH_TOKEN="<TFA Authorization Token>"

# INFLUX_HOST is the IP address of host where InfluxDB service is running
# It needs to be updated during deployment
export INFLUX_HOST="<Influx Public Host IP>"

# Use relative path to the current script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
