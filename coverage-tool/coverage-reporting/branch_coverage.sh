#!/usr/bin/env bash

##############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

#==============================================================================
# FILE: branch_coverage.sh
#
# DESCRIPTION: Generates intermediate layer json file and then
# code coverage HTML reports using LCOV report Open Source tool
#==============================================================================

set +x
set -e

ERROR_FILE=coverage_error.log

###############################################################################
# Prints error message to STDERR and log file.
# Globals:
# ERROR_FILE
# Arguments:
#   None
# Outputs:
#   Writes error to STDERR and log file with a timestamp
###############################################################################
err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" | tee -a ${ERROR_FILE} 1>&2
}

touch ${ERROR_FILE}
if ! [ -x "$(command -v lcov)" ]; then
  err 'Error: lcov is not installed. Install it with:\nsudo apt install lcov\n'
  exit 1
fi

###############################################################################
# Prints script usage.
# Arguments:
#   None
# Outputs:
#   Writes usage to stdout
###############################################################################
usage()
{
    # print the usage information
    printf "Usage: $(basename $0) [options]\n"
    printf "\t params:\n"
    printf "\t --config Configuration json file. Required.\n"
    printf "\t --workspace Local workspace folder where source codes reside. \
            Required.\n"
    printf "\t --json-path Intermediate json file name. Optional defaults to \
            'output_file.json'\n"
    printf "\t --outdir Report folder. Optional defaults to 'out'\n"
    printf "\t -h|--help Display usage\n"
    printf "Example of usage:\n"
    printf "./branch_coverage.sh --config config_file.json \
            --workspace /server_side/source/ --outdir html_report\n"
    exit 1
}

# default values
JSON_PATH=output_file.json
OUTDIR=out

###############################################################################
# Parse arguments.
# Globals:
# CONFIG_JSON
# LOCAL_WORKSPACE
# JSON_PATH
# OUTDIR
# Arguments:
#   Command line arguments
# Outputs:
#   Writes usage to stdout
###############################################################################
parse_arguments()
{
  while [ $# -gt 1 ]
  do
    key="$1"
    case $key in
      --config)
        CONFIG_JSON="$2"
        shift
      ;;
      --workspace)
        LOCAL_WORKSPACE="$2"
        shift
      ;;
      --json-path)
        JSON_PATH="$2"
        shift
      ;;
      --outdir)
        OUTDIR="$2"
        shift
      ;;
      -h|--help)
        usage
      ;;
      *)
        printf "Unknown argument $key\n"
        usage
      ;;
    esac
    shift
  done
}


parse_arguments $@

if [ -z "$LOCAL_WORKSPACE" ] || [ -z "$CONFIG_JSON" ]; then
    usage
fi

if [ ! -d "$LOCAL_WORKSPACE" ]; then
    err "$LOCAL_WORKSPACE doesn't exist\n"
    exit 1
fi

if [ ! -f "$CONFIG_JSON" ]; then
    err "$CONFIG_JSON doesn't exist\n"
    exit 1
fi

# clear may fail within a container-enviroment due to lack of
# TERM enviroment, so ignore this and other possible errors
clear || true

echo "Generating intermediate layer file '$JSON_PATH'..."
python3 intermediate_layer.py --config-json "$CONFIG_JSON" --local-workspace $LOCAL_WORKSPACE
echo "Converting intermediate layer file to info file..."
python3 generate_info_file.py --workspace $LOCAL_WORKSPACE --json $JSON_PATH
echo "Generating LCOV report at '$OUTDIR'..."
genhtml --branch-coverage coverage.info --output-directory $OUTDIR
mv coverage.info $OUTDIR/coverage.info
mv error_log.txt $OUTDIR/error_log.txt
