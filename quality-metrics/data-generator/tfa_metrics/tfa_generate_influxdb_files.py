#!/usr/bin/env python3

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" tfa_generate_influxdb_files.py:

    Parses the TF-A metrics summary files and generates JSON files
    containing data to be written to InfluxDB.
    Usage: python3 tfa_generate_influxdb_files.py --defectLog <defect log> \
                --complexityLog <complexity log> --loc <code churn loc> \
                --gitTagDate <tag date> --influxTime <git tag date & time>

"""

import argparse
import os
import re
import collections
import string
import time
import json


def load_module(name, fpath):
    """
    Function to return access to the module

    :param: name: Module name to be loaded
    :param: fpath: Relative path to complexity_parser.py
    :return: Module object
    """
    import os
    import imp
    return imp.load_source(
        name, os.path.join(
            os.path.dirname(__file__), fpath))


load_module(
    "complexity_parser",
    "../common_metrics/complexity_parser/complexity_parser.py")

from complexity_parser import ComplexityParser

def args_parse():

    global DEFECT_LOG
    global COMPLEXITY_LOG
    global CODE_CHURN
    global BASE_RELEASE_TAG
    global TARGET_RELEASE_TAG
    global GIT_TAG_DATE
    global GIT_TAG_DATE_TIME

    # Create parser instance and add arguments
    parser = argparse.ArgumentParser(
        description="TF-A quality metrics InfluxDB JSON files generator")
    parser.add_argument("--defectLog", help="name of the defect log")
    parser.add_argument("--complexityLog", help="name of the complexity log")
    parser.add_argument("--loc", help="code churn statistics", required=True)
    parser.add_argument(
        "--baseTag",
        help="name of the base release tag",
        required=True)
    parser.add_argument(
        "--targetTag",
        help="name of the target release tag",
        required=True)
    parser.add_argument("--gitTagDate", help="Git Tag Date", required=True)
    parser.add_argument(
        "--influxTime",
        help="InfluxDB time, which is Git Tag Date and Time",
        required=True)

    # Parse the arguments
    args = parser.parse_args()

    if args.defectLog:
        DEFECT_LOG = args.defectLog

    if args.complexityLog:
        COMPLEXITY_LOG = args.complexityLog

    if args.loc:
        CODE_CHURN = args.loc

    if args.baseTag:
        BASE_RELEASE_TAG = args.baseTag

    if args.targetTag:
        TARGET_RELEASE_TAG = args.targetTag

    if args.gitTagDate:
        GIT_TAG_DATE = re.sub('[-]', '', args.gitTagDate)

    if args.influxTime:
        GIT_TAG_DATE_TIME = args.influxTime


def tfa_generate_defect_data(data):
    """
    Function to write the data of defects into influxdb """

    dict_list = []
    runDate = time.strftime('%H:%M-%x')

    # "Issue_Status" acts as an indicative field to help the viewer figure out
    # the current status of the bug
    defects_tracking = {
        "metadata": {
            "metrics": "tfa_defects_tracking"
        },
        "api_version": "1.0",
        "data": [{
            "measurement": "TFA_Defects_Tracking",
            "fields": {
                "Issue_Status": "{}".format("Open"),
                "Number_of_Defects": int(len(data))
            },
            "tags": {
                "Measured_Date": "{}".format(runDate)
            },
        }]
    }

    with open('defects_tracking.json', 'w') as fp:
        json.dump(defects_tracking, fp)

    # Write details of each defects into the other measurement called
    # "TFA_Defects_Statistics"
    defect_stats = {}
    defect_stats["data"] = []
    defect_stats["metadata"] = {}
    defect_stats["metadata"]["metrics"] = "tfa_defects_stats"
    defect_stats["api_version"] = "1.0"
    for ID, description in data.items():
        json_body = {
            "measurement": "TFA_Defects_Statistics",
            "fields": {
                "Title": "{}".format(description['title']),
                "Issue_Status": "{}".format(description['state']),
                "URL": "{}".format(description['url'])
            },
            "tags": {
                "Defect_ID": "{}".format(ID),
                "Measured_Date": "{}".format(runDate)
            }
        }

        defect_stats["data"].append(json_body)

    with open('defects_statistics.json', 'w') as fp:
        json.dump(defect_stats, fp)


def tfa_generate_codechurn_data(data, base_tag, target_tag):
    """
        Generates InfluxDB data for TF-A code churn and
        writes that to code_churn.json file.

        :param: data: Lines of change
        :param: base_tag: Release tag prior to target_tag
        :param: target_tag: Tag being tested
    """

    json_body = {
        "metadata": {
            "metrics": "tfa_code_churn"
        },
        "api_version": "1.0",
        "data": [{
            "measurement": "TFA_CodeChurn_Tracking",
            "fields": {
                "Lines_of_Change": int(data)
            },
            "tags": {
                "Git_Tag_Date": int(GIT_TAG_DATE),
                "Base_Tag": "{}".format(base_tag),
                "Target_Tag": "{}".format(target_tag)
            },
            "time": GIT_TAG_DATE_TIME
        }]
    }

    with open('code_churn.json', 'w') as fp:
        json.dump(json_body, fp)


def tfa_generate_complexity_data(data, base_tag, target_tag, threshold):
    """
        Generates InfluxDB data for TF-A complexity scores and
        writes that to complexity stats and tracking json files.

        :param: data: Complexity data
        :param: base_tag: Release tag prior to target_tag
        :param: target_tag: Tag being tested
        :param: threshold: Complexity threshold
    """

    complexity_stats = {}
    complexity_stats["data"] = []
    complexity_stats["metadata"] = {}
    complexity_stats["metadata"]["metrics"] = "tfa_complexity_stats"
    complexity_stats["api_version"] = "1.0"

    totalComplexity = 0

    print(
        "@@ Number of functions with complexity score > %d: %d" %
        (threshold, len(data)))

    for k, v in data.items():
        # Extract the location and function name
        location = k.split(':', 1)[0].strip()
        functionID = k.split(':', 1)[1].strip()
        json_body = {
            "measurement": "TFA_Complexity_Statistics",
            "fields": {
                "Function_ID": "{}".format(functionID),
                "Score": int(v),
                "Whitelisted": "{}".format("no"),
                "Threshold": int(threshold)
            },
            "tags": {
                "Location": "{}".format(location),
                "Git_Tag_Date": int(GIT_TAG_DATE),
                "Base_Tag": "{}".format(base_tag),
                "Target_Tag": "{}".format(target_tag)
            },
            "time": GIT_TAG_DATE_TIME
        }

        complexity_stats["data"].append(json_body)
        totalComplexity += int(v)

    with open('complexity_stats.json', 'w') as fp:
        json.dump(complexity_stats, fp)

    totalExceedThreshold = len(data)
    complexity_tracking = {
        "metadata": {
            "metrics": "tfa_complexity_tracking"
        },
        "api_version": "1.0",
        "data": [{
            "measurement": "TFA_Complexity_Tracking",
            "fields": {
                "Threshold": int(threshold),
                "Whitelisted": "{}".format("no"),
                "Functions_Exceeding_Threshold_Not_Whitelisted": int(totalExceedThreshold)
            },
            "tags": {
                "Git_Tag_Date": int(GIT_TAG_DATE),
                "Target_Tag": "{}".format(target_tag)
            },
            "time": GIT_TAG_DATE_TIME
        }]
    }

    with open('complexity_tracking.json', 'w') as fp:
        json.dump(complexity_tracking, fp)


class DefectParser(object):
    """
        Extract the following data from the defect/complexity logs:
            - defect list: {test class ID:{title: <title>, link: <URL>}}
            - int variable: total number of defects
    """

    def __init__(self, defectLog):
        self.defectLog = defectLog
        self.defectDict = collections.OrderedDict()

        self.process_defect_log()

    def process_defect_log(self):
        """
            Function to process defect log and populate the defect dictionary
        """
        with open(self.defectLog) as fp:
            content = fp.readlines()

        baseURL = "https://github.com/ARM-software/tf-issues/issues/"

        # Get defect id, title and URL link to populate the defect dictionary
        for i in content:
            i_strip = i.strip()

            titleIDRegex = "^Found open bug with id: ([0-9]+): (.*)"
            mIDTitle = re.match(titleIDRegex, i)

            if mIDTitle:
                defectID = mIDTitle.group(1)
                defectTitle = mIDTitle.group(2)
                defectURL = baseURL + mIDTitle.group(1)

                self.defectDict[defectID] = {}
                self.defectDict[defectID]['title'] = defectTitle.split(',')[0]
                self.defectDict[defectID]['url'] = defectURL
                self.defectDict[defectID]['state'] = defectTitle.split(',')[1]


if __name__ == "__main__":

    # Initialise global variables
    DEFECT_LOG = ""
    COMPLEXITY_LOG = ""
    CODE_CHURN = 0
    BASE_RELEASE_TAG = 0
    TARGET_RELEASE_TAG = 0
    # Functions having pmcabbe cylomatic complexity >= TFA_THRESHOLD
    # are reported
    TFA_THRESHOLD = 11
    GIT_TAG_DATE = ""

    # parse arguments
    args_parse()

    # Generate defect data
    defectData = DefectParser(DEFECT_LOG)

    # Generate complexity data
    complexityData = ComplexityParser(COMPLEXITY_LOG, TFA_THRESHOLD)

    tfa_generate_defect_data(defectData.defectDict)

    tfa_generate_codechurn_data(
        CODE_CHURN,
        BASE_RELEASE_TAG,
        TARGET_RELEASE_TAG)

    tfa_generate_complexity_data(
        complexityData.complexityDict,
        BASE_RELEASE_TAG,
        TARGET_RELEASE_TAG,
        TFA_THRESHOLD)
