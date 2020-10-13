#!/usr/bin/env bash

#======================================================================
# Copyright (c) 2020, Arm Limited. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
#======================================================================

#======================================================================
# FILE: tfa_quality_metrics.sh
#
# DESCRIPTION: script to defects and calculate complexity score for arm-trusted-firmware
#
# USAGE: ./tfa_quality_metrics.sh --tag <release tag>
#
#======================================================================
. ../common_metrics/common_utilities/common_utilities.sh
. ./tfa_variables.sh

# === Function ========================================================
# NAME: clone_git_repo
# DESCRIPTION: Clones the repository via "git clone" command
# =====================================================================
clone_git_repo()
{
  REPO_URL=$1
  REPOSITORY=$(basename $REPO_URL .git)
  # If repository already exists, then return from this function
  if [ -d $REPOSITORY ]; then
    printf "\nRepository \"$REPOSITORY\" already exists."
    return
  fi

  # Clone repo. If it doesn't exist, then exit.
  printf "\nCloning $REPOSITORY...\n"
  printf "git clone $REPO_URL\n"
  clone_err=$(git clone "$REPO_URL" 2>&1 | grep "fatal")

  if [[ ! -z $clone_err ]]; then
    printf "Repository \"$REPOSITORY\" not found. Exiting...\n"
    exit
  fi
}

# === Function ========================================================
# NAME: tag_validation
# DESCRIPTION: Invokes get_base_tag which retrieves base tag is target
#              tag is valid
# PARAMETER:
#   $1: tag id
# =====================================================================
tag_validation()
{
  tag=$1

  # check that tag actually exists
  pushd arm-trusted-firmware
  get_base_tag "^v[0-9]+\.[0-9]+$"
  popd
}

# === Function ========================================================
# NAME: generate_defect_summary
# DESCRIPTION: Calculates the number of the total defects
# PARAMETER:
#   $1: output defect log
# =====================================================================
generate_defect_summary()
{
  # copy the github module to this level
  cp $DIR/./githubpy/github.py .
  cp $DIR/./githubpy/setup.py .

  python3 $DIR/tfa_defects.py > $DEFECT_LOG
}

# === Function ========================================================
# NAME: get_complexity_score
# DESCRIPTION: Finds cyclomatic complexity of all the C/C++ files.
# =====================================================================
get_complexity_score()
{
  complexity_dir="$(basename $TFA_REPO .git)"

  # check the availability of pmccabe
  validation=$(which pmccabe)
  if [ -z "$validation" ]; then
    echo "pmccabe not found. Aborting test...\n"
    exit
  fi

  # find out complexity on computed folder
  pmccabe -vt `find $complexity_dir -name "*.c"` `find $complexity_dir -name "*.cpp"` > $COMPLEXITY_LOG
}

# === Function ========================================================
# NAME: complexity_score
# DESCRIPTION: Calculates the McCabe complexity score
# =====================================================================
complexity_score()
{
  # checkout the tag before running pmmcabe
  pushd $DIR/arm-trusted-firmware

  echo "git checkout ${TARGET_TAG}"
  git checkout ${TARGET_TAG}
  git status

  # exclude subfolders under plat except for 'arm' and 'common'
  mv plat tmp_plat
  mkdir plat
  cp -rp tmp_plat/arm tmp_plat/common tmp_plat/compat plat 2>/dev/null
  rm -rf tmp_plat

  # exclude subfolders under lib
  rm -rf lib/stdlib
  rm -rf lib/libfdt
  rm -rf lib/compiler-rt

  # exclude tools
  rm -rf tools

  # exclude services/spd except for 'tspd'
  mv services/spd services/safe_spd
  mkdir services/spd
  cp -rp services/safe_spd/tspd services/spd 2>/dev/null
  rm -rf services/safe_spd

  popd

  get_complexity_score
}

# === Function ========================================================
# NAME: code_churn_summary
# DESCRIPTION: Function to get code churn summary
# PARAMETER:
#   $1: code churn log
# =====================================================================
code_churn_summary()
{
  pushd $DIR/arm-trusted-firmware

  echo "@@ Calculating code churn excluding plat folder..."

  # Calculate code churn
  stats1=$(git diff --stat $BASE_TAG $TARGET_TAG  -- . ':!plat' | grep -E "[0-9]+ file(s)? changed,")
  CODE_CHURN1=$(generate_code_churn_summary "$stats1")

  echo "@@ Calculating code churn plat/arm and plat/common folder..."
  stats2=$(git diff --stat $BASE_TAG $TARGET_TAG  -- 'plat/arm' 'plat/common' | grep -E "[0-9]+ file(s)? changed,")
  CODE_CHURN2=$(generate_code_churn_summary "$stats2")

  CODE_CHURN=$((CODE_CHURN1+CODE_CHURN2))
  echo "Code churn: $CODE_CHURN  LOC" | tee $DIR/$CODE_CHURN_LOG

  # get tagger date for git tag in YYYY-MM-DD format
  get_git_tag_date

  popd

  echo $CODE_CHURN
}

# === Function ========================================================
# NAME: write_influxdb_data
# DESCRIPTION: Function to generate JSON files containing DB data
# =====================================================================
write_influxdb_data()
{
  # Create a result folder using the current time stamp and
  # copy InfluxDB json files to it
  local resultDir=$(date +%Y-%m-%d_%H_%M_%S)
  local_result=$DIR/$resultDir

  mkdir -p $local_result
  mv *.json *.txt $local_result

  pushd $local_result

  for json_file in *.json; do
    curl -X POST -H "Content-Type: application/json" -d "$(cat ${json_file})" \
      "http://${INFLUX_HOST}:5000" -H "${TFA_METRICS_AUTH_TOKEN}"
  done

  popd
}

# === Function ========================================================
# NAME: generate_defect_codechurn_complexity_data
# DESCRIPTION: Function to generate defects, code churn and complexity
#   quality metrics data for given tag.
# =====================================================================
generate_defect_codechurn_complexity_data()
{
  # Remove files from previous run, if any
  rm -rf arm-trusted-firmware/ github* setup.py

  clone_git_repo $TFA_REPO
  clone_git_repo $GITHUBPY_REPO

  # validate TARGET_TAG and get base tag
  tag_validation $TARGET_TAG

  # do defect statistics
  generate_defect_summary

  # cyclomatic complexity check
  complexity_score

  # code churn
  code_churn_summary

  # Create InfluxDB json files to be written to InfluxDB
  python3 $DIR/tfa_generate_influxdb_files.py --defectLog $DEFECT_LOG \
    --complexityLog $COMPLEXITY_LOG --loc $CODE_CHURN --baseTag $BASE_TAG \
    --targetTag $TARGET_TAG --gitTagDate $GIT_TAG_DATE --influxTime "$GIT_TAG_DATE_TIME"
}

# === Function ========================================================
# NAME: usage
# DESCRIPTION: Function to print script usage
# =====================================================================
usage()
{
  # print usage common to all files
  printf "USAGE: $(basename $0) [options]\n"
  printf "\t params: \n"
  printf "\t -h|--help            print help information\n"
  printf "\t --tag                user specified release tag\n"
  printf "\t --metric_type        [ runtime_instrumentation | image_size | coverity_misra ]*\n"
  printf "\t --rt_instr_file      Path to file containing instrumentation data\n"
  printf "\t                      Required when metric_type is runtime_instrumentation\n"
  printf "\t --image_size_file    Path to file containing image size data\n"
  printf "\t                      Required when metric_type is image_size\n"
  printf "\t --misra_defects_file Path to file containing MISRA defects information\n"
  printf "\t                      Required when metric_type is coverity_misra\n"
  printf "* By default, code coverage, defects and complexity metrics are generated for given tag\n"
  printf "When metric_type is specified, corresponding data file to be parsed is also required\n"
  exit
}

# === Function ========================================================
# NAME: generate_tfa_metrics_data
# DESCRIPTION: Function to generate InfluxDB JSON file for specified
#   TF-A metrics - run time instrumentation/image size/MISRA defects
# =====================================================================
generate_tfa_metrics_data()
{
  case $METRIC_TYPE in
    runtime_instrumentation)
      if [[ ! -f $RTINSTR_FILE ]]; then
        echo "$RTINSTR_FILE doesn't exist.. Exiting.."
        exit 1
      else
        python3 tfa_rt_instr.py --rt_instr $RTINSTR_FILE
      fi
    ;;
    image_size)
      if [[ ! -f $IMAGE_SIZE_FILE ]]; then
        echo "$IMAGE_SIZE_FILE doesn't exist.. Exiting.."
        exit 1
      else
        python3 tfa_track_image_size.py --image_size_file $IMAGE_SIZE_FILE
      fi
    ;;
    coverity_misra)
      if [[ ! -f $MISRA_DEFECTS_FILE ]]; then
        echo "$MISRA_DEFECTS_FILE doesn't exist.. Exiting.."
        exit 1
      else
        python3 tfa_track_misra_defects.py --misra_defects_file $MISRA_DEFECTS_FILE
      fi
    ;;
  esac
  write_influxdb_data
  exit
}

# === Function ========================================================
# NAME: parse_args
# DESCRIPTION: Arguments parser function
# =====================================================================
parse_args()
{
  # parse the arguments
  while [[ $# -gt 0 ]]
  do
    key="$1"
    case $key in
      -h|--help)
        usage
      ;;
      --tag)
        export TARGET_TAG="$2"
        shift
        shift
      ;;
      --metric_type)
        export METRIC_TYPE="$2"
        shift
        shift
      ;;
      --rt_instr_file)
        export RTINSTR_FILE="$2"
        shift
        shift
      ;;
      --image_size_file)
        export IMAGE_SIZE_FILE="$2"
        shift
        shift
      ;;
      --misra_defects_file)
        export MISRA_DEFECTS_FILE="$2"
        shift
        shift
      ;;
      *)
        echo "Unknown argument $key in arguments $@"
        usage
      ;;
    esac
  done

}

# === Function ========================================================
# NAME: main
# DESCRIPTION: main function
# PARAMETER: Command-line arguments
# =====================================================================
main()
{
  parse_args $@

  # If metrics type is specified, then generate influxdb JSON files
  # from given text files
  if [[ ! -z $METRIC_TYPE ]]; then
    generate_tfa_metrics_data
  # Otherwise generate code churn, complexity and defects data for given tag
  elif [[ ! -z $TARGET_TAG ]]; then
    generate_defect_codechurn_complexity_data
  else
    echo "Please specify either metric_type or tag.."
    usage
  fi

  # write generated data (JSON files) to InfluxDB
  write_influxdb_data
}

main $@
