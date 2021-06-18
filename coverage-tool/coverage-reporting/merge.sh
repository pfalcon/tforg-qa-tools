#!/usr/bin/env bash

##############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: GPL-2.0-only
##############################################################################

#==============================================================================
# FILE: merge.sh
#
# DESCRIPTION: Wrapper to merge intermediate json files and LCOV trace .info
# files.
#==============================================================================

set +x
#################################################################
# Function to manipulate json objects.
# The json object properties can be accessed through "." separated
# property names. There are special characters that define a function
# over a given property value:
# If the qualifier list starts with '-' then is asking for the len of the
# json array defined by the qualifiers.
# If the qualifier list starts with '*' then the resulting json value
# is returned without double quotes at the end and the beginning.
# If some property name starts with "?" then is requesting if that
# property exists within the json object.
# Globals:
#   None
# Arguments:
#   1-Json string that describes the json object
#   2-String of '.' separated qualifiers to access properties
#       within the json object
#   3- Optional default value for a sought property value
# Outputs:
#   None
################################################################
get_json_object() {
  export _json_string="$1"
  export _qualifiers="$2"
  export _default="$3"
  python3 - << EOT
import os
import json
import sys

_json_string = os.getenv("_json_string", "")
_qualifiers = os.getenv("_qualifiers", "")
_default = os.getenv("_default", "")
try:
    data = json.loads(_json_string)
except Exception as ex:
    print("Error decoding json string:{}".format(ex))
    sys.exit(-1)
ptr = data
if _qualifiers[0] in ['-', '*']:
    cmd = _qualifiers[0]
    _qualifiers = _qualifiers[1:]
else:
    cmd = ""
for _name in _qualifiers.split("."):
    if _name in ptr:
        ptr = ptr[_name]
    elif _name.isdigit() and int(_name) < len(ptr):
        ptr = ptr[int(_name)]
    elif _name.startswith("?"):
        print(_name[1:] in ptr)
        sys.exit(0)
    elif _default:
        print(_default)
        sys.exit(0)
    else:
        print("'{}' is not in the json object".format(_name))
        sys.exit(-1)
if cmd == "-":
    # return len of the json array
    print(len(ptr))
elif cmd == "*":
    #remove quotes
    string = json.dumps(ptr)
    if string.startswith('"') and string.endswith('"'):
        string = string[1:-1]
    print(string)
else:
    print(json.dumps(ptr))
EOT
}

#################################################################
# Convert a relative path to absolute path
# Globals:
#   None
# Arguments:
#   1-Path to be converted
# Outputs:
#   Absolute path
################################################################
get_abs_path() {
  path="$1"
  echo "$(cd $(dirname $path) && echo "$(pwd -P)"/$(basename $path))"
}

#################################################################
# Clone the source files
# Globals:
#   None
# Arguments:
#   1-Json file with the sources to be cloned
#   2-Folder where to clone the sources
# Outputs:
#   None
################################################################
clone_repos() {
  export OUTPUT_JSON="$1"
  export CSOURCE_FOLDER="${2:-$LOCAL_WORKSPACE}"

  cd $DIR # To be run at the same level of this script
python3 - << EOT
import os
import clone_sources

output_file = os.getenv('OUTPUT_JSON', 'output_file.json')
source_folder = os.getenv('CSOURCE_FOLDER', 'source')
try:
    r = clone_sources.CloneSources(output_file)
    r.clone_repo(source_folder)
except Exception as ex:
    print(ex)
EOT
    cd -
}

#################################################################
# Get the a file defined in the json object
# Globals:
#   None
# Arguments:
#   1-Json object that defines the locations of the info and json
#       files
#   2-Folder to save the info and json files
#   3-Variable that holds the name of the variable that will hold
#       the name of the file to be downloaded (reference argument)
# Outputs:
#   None
################################################################
get_file() {
  json_object="$1"
  where="$2"
  var_name="${3:-param_cloned}" # Defaults to globar var

  local _type=$(get_json_object "$json_object" "type")
  local _origin=$(get_json_object "$json_object" "*origin")
  local _compression=$(get_json_object "$json_object" "*compression" None)
  local fname=""
  local cloned_file=""
  local full_filename=$(basename -- "$_origin")
  local extension="${full_filename##*.}"
  local filename="${full_filename%.*}"

  if [ "$_type" = '"http"' ];then
    fname="$where.$extension" # Same filename as folder
    rm $where/$fname &>/dev/null || true
    wget -o error.log $_origin -O $where/$fname || (
            cat error.log && exit -1)
    cloned_file="$(get_abs_path $where/$fname)"
  elif [ "$_type" = '"bundle"' ];then
    # Check file exists at origin, i.e. was unbundled before
    fname="$_origin"
    if [ -f "$where/$fname" ];then
        cloned_file="$(get_abs_path $where/$fname)"
    fi
  elif [ "$_type" = '"file"' ];then
    if [[ "$_origin" = http* ]]; then
        echo "$_origin looks like 'http' rather than 'file' please check..."
        exit -1
    fi
    fname="$where.$extension" # Same filename as folder
    cp -f $_origin $where/$fname
    cloned_file="$(get_abs_path $where/$fname)"
  else
    echo "Error unsupported file type:$_type.... Aborting."
    exit -1
  fi
  if [ "$_compression" = "tar.xz" ];then
    cd $where
    pwd
    tar -xzf $fname
    rm -f $fname
    cd -
  fi
  eval "${var_name}=${cloned_file}"
}

#####################################################################
# Get (download/copy) info and json files from the input json file
# Globals:
#   merge_input_json_file: Input json file with locations of info
#                          and intermediate json files to be merged.
#   input_folder: Folder to put info and json files to be merged
# Arguments:
#   None
# Outputs:
#   None
###################################################################
get_info_json_files() {
  json_string="$(cat $merge_input_json_file)"
  nf=$(get_json_object "$json_string" "-files")
  rm -rf $input_folder > /dev/null || true
  mkdir -p $input_folder
  for f in $(seq 0 $(($nf - 1)));
  do
    pushd $input_folder > /dev/null
    _file=$(get_json_object "$json_string" "files.$f")
    folder=$(get_json_object "$_file" "*id")
    echo "Geting files from project '$folder' into '$input_folder'..."
    mkdir -p $folder
    bundles=$(get_json_object "$_file" "bundles" None)
    if [ "$bundles" != "None" ];then
      nb=$(get_json_object "$_file" "-bundles")
      for n in $(seq 0 $(($nb - 1)));
      do
        get_file "$(get_json_object "$bundles" "$n")" $folder
      done
    fi
    get_file "$(get_json_object "$_file" "config")" $folder config_json_file
    get_file "$(get_json_object "$_file" "info")" $folder info_file
    popd > /dev/null
  done
}

#################################################################
# Merge json and info files and generate branch coverage report
# Globals:
#   output_coverage_file: Location and name for merge coverage info
#   output_json_file: Location and name for merge json output
#   input_folder: Location where reside json and info files
#   LOCAL_WORKSPACE: Local workspace folder with the source files
# Arguments:
#   None
# Outputs:
#   Output merge coverage file
#   Output merge json file
################################################################
merge_files() {
# Merge info and json files
  local lc=" "
  if [ -n "$LOCAL_WORKSPACE" ];then
    # Translation to be done in the info files to local workspace
    lc=" --local-workspace $LOCAL_WORKSPACE"
  fi
  # Getting the path of the merge.py must reside at the same
  # path as the merge.sh
  python3 ${DIR}/merge.py \
      $(find $input_folder -name "*.info" -exec echo "-a {}" \;) \
      $(find $input_folder -name "*.json" -exec echo "-j {}" \;) \
      -o $output_coverage_file \
      -m $output_json_file \
      $lc

}


#################################################################
# Print scripts usage
# Arguments:
#   None
# Outputs:
#   Prints to stdout script usage
################################################################
usage() {
  clear
  echo "Usage:"
  echo "merge -h              Display this help message."
  echo "-j <input json file>  Input json file(info and intermediate json files to be merged)."
  echo "-l <report folder>    Folder for branch coverage report. Defaults to ./lcov_folder."
  echo "-i <Path>             Folder to copy/download info and json files. Defaults to ./input."
  echo "-w <Folder>           Local workspace folder for source files."
  echo "-o <name>             Name of the merged info file. Defaults to ./coverage_merge.info"
  echo "-m <name>             Name of the merged metadata json file. Defaults to ./merge_output.json"
  echo "-c                    If it is set, sources from merged json files will be cloned/copied to local workspace folder."
  echo "$help_message"
}

help_message=$(cat <<EOF

# The script that merges the info data (code coverage) and json metadata
# (intermediate layer) needs as an input a json file with the following
# properties:
# files: array of objects that describe the type of file/project to be
# merged.
#   id: Unique identifier (project) associated to the info and
#       intermediate json files
#   config: Intermediate json file
#       type: Type of storage for the file. (http or file)
#       origin: Location (url or folder) of the file
#   info:  Info file
#       type: Type of storage for the file. (http or file)
#       origin: Location (url or folder) of the file
# Example:
{ "files" : [
                {
                    "id": "<project 1>",
                    "config":
                        {
                            "type": "http",
                            "origin": "<URL of json file for project 1>"
                        },
                    "info":
                        {
                            "type": "http",
                            "origin": "<URL of info file for project 1>"
                        }
                },
                {
                    "id": "<project 2>",
                    "config":
                        {
                            "type": "http",
                            "origin": "<URL of json file for project 2>"
                        },
                    "info":
                        {
                            "type": "http",
                            "origin": "<URL of info file for project 2>"
                        }
                },
                .
                .
                .
        ]
}
EOF
)

clear
# Local workspace folder to contain source files
LOCAL_WORKSPACE=""
# If this is true then will clone/copy sources from merged json
# file into local workspace
CLONE_SOURCES=false
# Location of the input json file that contains information about
# the info and json files to be merged and produced a report
merge_input_json_file=""
# Folder to download json and info files
input_folder="./input_folder"
# Folder to to put the reports
LCOV_FOLDER="./lcov_folder"
# File name for merge coverage info
output_coverage_file="./coverage_merge.info"
# File name for merge json output
output_json_file="./merge_output.json"
while getopts ":hj:o:l:w:i:cm:" opt; do
  case ${opt} in
    h )
      usage
      exit 0
      ;;
    w )
      LOCAL_WORKSPACE=$(cd $OPTARG; pwd)
      ;;
    i )
      input_folder=$OPTARG
      ;;
    c )
      CLONE_SOURCES=true
      ;;
    j )
      merge_input_json_file=$OPTARG
      ;;
    l )
      LCOV_FOLDER=$OPTARG
      ;;
    o )
      output_coverage_file=$OPTARG
      ;;
    m )
      output_json_file=$OPTARG
      ;;
    \? )
      echo "Invalid option: $OPTARG" 1>&2
      usage
      exit -1
      ;;
    : )
      echo "Invalid option: $OPTARG requires an argument" 1>&2
      usage
      exit -1
      ;;
  esac
done
shift $((OPTIND -1))
if [ -z "$merge_input_json_file" ]; then
  echo "Input json file required"
  usage
  exit -1
fi
if [ -z "$LOCAL_WORKSPACE" ] && [ $CLONE_SOURCES = true ]; then
    echo "Need to define a local workspace folder to clone/copy sources!"
    exit -1
fi
# Getting the script folder where other script files must reside, i.e
# merge.py, clone_sources.py
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
input_folder="$(get_abs_path $input_folder)"
LCOV_FOLDER="$(get_abs_path  $LCOV_FOLDER)"
output_coverage_file="$(get_abs_path $output_coverage_file)"
output_json_file="$(get_abs_path $output_json_file)"
param_cloned=""
get_info_json_files
merge_files
if [ $CLONE_SOURCES = true ];then
    clone_repos $output_json_file
fi
# Generate branch coverage report
genhtml --branch-coverage $output_coverage_file \
    --output-directory $LCOV_FOLDER
cd -
