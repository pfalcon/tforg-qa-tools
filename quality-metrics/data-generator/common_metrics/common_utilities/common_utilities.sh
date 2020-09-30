#!/usr/bin/env bash

#======================================================================
# Copyright (c) 2020, Arm Limited. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
#======================================================================

#===============================================================================
# FILE: common_utilities.sh
#
# DESCRIPTION: Contains common utilities required by all the metrics
#===============================================================================

# === Function ========================================================
# NAME: include_variables_file
# DESCRIPTION: Includes the variables file, specific to repository for
#              which metics are being computed. For example, include and
#              exclude folders are different for different repositories
# PARAMETERS:
#    $1: File containing variables specific to the repository for which
#        metrics are computed.
# =====================================================================
include_variables_file()
{
  . ./"${1}"
}


# === Function ========================================================
# NAME: cleanup_and_exit
# DESCRIPTION: Deletes a repository, if it exists, and exits
# =====================================================================
cleanup_and_exit()
{
  # Delete the cloned repository
  if [ -d "$REPOSITORY" ]; then
    printf "Deleting $REPOSITORY...\n"
    rm -rf $REPOSITORY
  fi

  printf "Exiting...\n"
  exit
}

# === Function ========================================================
# NAME: generate_code_churn_summary
# DESCRIPTION: Generates the code churn summary from stats
# PARAMETER:
#   $1: STATS
# =====================================================================
generate_code_churn_summary()
{
  INS_DEL_LOC_EXTRACT="[0-9]+ file(s)? changed, ([0-9]+) insertion(s)?\(\+\), ([0-9]+) deletion(s)?\(\-\)"
  INS_LOC_EXTRACT="[0-9]+ file(s)? changed, ([0-9]+) insertion(s)?\(\+\)"
  DEL_LOC_EXTRACT="[0-9]+ file(s)? changed, ([0-9]+) deletion(s)?\(\-\)"
  if [[ $1 =~ ${INS_DEL_LOC_EXTRACT} ]]; then
    INS=${BASH_REMATCH[2]}
    DEL=${BASH_REMATCH[4]}
  elif [[ $1 =~ ${INS_LOC_EXTRACT} ]]; then
    INS=${BASH_REMATCH[2]}
    DEL=0
  elif [[ $1 =~ ${DEL_LOC_EXTRACT} ]]; then
    INS=0
    DEL=${BASH_REMATCH[2]}
  else
    INS=DEL=0
  fi

  CODE_CHURN=$((INS+DEL))
  echo "$CODE_CHURN"
}

# === Function ========================================================
# NAME: get_git_tag_date
# DESCRIPTION: Returns the git tag date, as follows:
#              1. tagger date is returned for annotated tag
#              2. creator date is returned for non-annotated tag
# =====================================================================
get_git_tag_date()
{
  GIT_TAG_DATE_TIME=''
  GIT_TAG_DATE=''

  if [ -n "$1" ]; then
    tag=$1
  else
    tag=$TARGET_TAG
  fi
  # Get tagger date for git tag in YYYY-MM-DD format
  GIT_TAG_DATE_TIME=$(git rev-parse $tag | xargs git cat-file -p | \
                      awk '/^tagger/ { print strftime("%F",$(NF-1))}')
  # If tagger date is not returned (in case of non-annotated tag), then get created date
  if [ -z "${GIT_TAG_DATE}" ]; then
    printf "\nGit tag date is \"created date\" because $tag is non-annotated...\n"
    GIT_TAG_DATE_TIME=$(git log -1 --format=%ai $tag)
  else
    printf "\nGit tag date is \"tagger date\" because $tag is annotated...\n"
  fi
  export GIT_TAG_DATE_TIME
  arr=($GIT_TAG_DATE_TIME)
  export GIT_TAG_DATE=${arr[0]}
}

# === Function =================================================================
# NAME: get_base_tag
# DESCRIPTION: Checks if target tag exists. If it is exists, get the base tag
# ==============================================================================
get_base_tag()
{
  # list git tag by commit date and extract the tag string
  tagList=$(git tag | xargs -I@ git log --format=format:"%ai @%n" -1 @ | sort | awk '{print $4}')

  tagArray=($tagList)
  matched=0

  prevTag=""
  currentTag=""
  counter=0
  TAG_PATTERN=$1

  # Check if target tag exists
  for i in "${tagArray[@]}"; do
    if [ "$i" == "$tag" ]; then
      matched=1
      currentTag=$i
      break
    else
      # If not in form of vXXX.YYY, continue
      counter=$((counter+1))
      continue
    fi
  done

  if [ $matched -eq 0 ]; then
    printf "@@ Tag $tag does not exist. Please specify an existing one.\n"
    echo "Existing Tags:"
    git tag | xargs -I@ git log --format=format:"%ai @%n" -1 @ | sort | awk '{print $4}'
    exit
  fi

  get_git_tag_date "$tag"
  tag_date_1=$GIT_TAG_DATE

  # Search for previous tag in the form of vXXX.YYY before the current tag
  # Skip the current tag itself and find the first match
  START=$((counter-1))
  for ((i=${START};i>=0;i--)); do
    temp_tag="${tagArray[$i]}"
    get_git_tag_date "$temp_tag"
    tag_date_2=$GIT_TAG_DATE
    echo "$temp_tag $GIT_TAG_DATE $tag_date_2"
      if [[ $temp_tag =~ $TAG_PATTERN ]] && [[ "$tag_date_1" != "$tag_date_2" ]]; then
        prevTag=$temp_tag
        break
      fi
  done

  printf "@@ Tag $tag is valid\n"
  export TARGET_TAG=$currentTag
  export BASE_TAG=$prevTag
  echo "@@ Target tag is $TARGET_TAG ($tag_date_1)"
  echo "@@ Base tag is $BASE_TAG ($tag_date_2)"
}
