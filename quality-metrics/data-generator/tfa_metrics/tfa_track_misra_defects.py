#!/usr/bin/env python

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" tfa_track_misra_defects.py:

       Parses TFA MISRA defects file, stores the data in a list of
       dictionaries and creates JSON file to be written to influxDB.

       USAGE: python3 tfa_track_misra_defects.py --misra_defects_file <DefectsFile.txt>

   """

import argparse
import os.path
import re
import json


class TFACoverityFileParser:
    """
        Store the Misra C defects data in a list of dictionaries in the following
        format:
            [
                {
                    "measurement": <build_config>,
                    "fields" : {
                        "TotalDefects"    : Total coverity defects
                        "MandatoryDefects": Mandatory defects
                        "RequiredDefects" : Required defects
                        "AdvisoryDefects" : Advisory defects
                    },
                    "tags" : {
                        "BinMode"         : Type of build (Release|Debug)
                        "CommitID"        : Commit ID
                        "CommitTitle"     : Commit Title
                    }
                    "time" : PR Merge Commit Time
                }
            ]
    """

    file_dict = {}
    file_name = None

    def __init__(self, input_file):
        self.file_name = input_file
        self.parse_misra_defects_file()
        print(json.dumps(self.file_dict, indent=4, sort_keys=True))

    def parse_misra_defects_file(self):
        self.file_dict = {}
        self.file_dict['tags'] = {}
        self.file_dict['fields'] = {}

        with open(self.file_name) as fp:
            # Store measurement name as build config
            line = fp.readline()
            val = line.split(':')
            if val[0].strip() != 'BuildConfig':
                print("Invalid file format.. BuildConfig not found..")
                print("Exiting..")
                exit()
            self.file_dict['measurement'] = val[1].strip()

            # Store bin_mode
            line = fp.readline()
            val = line.split(':')
            if val[0].strip() != 'BinMode':
                print("Invalid file format.. BinMode not found..")
                print("Exiting..")
                exit()
            self.file_dict['tags'][val[0].strip()] = val[1].strip().title()

            # Store Commit ID
            line = fp.readline()
            val = line.split(':')
            if val[0].strip() != 'CommitID':
                print("Invalid file format.. Commit ID not found..")
                print("Exiting..")
                exit()
            self.file_dict['tags'][val[0].strip()] = val[1].strip()[0:10]

            # Store Commit Title
            line = fp.readline()
            val = line.split(':', 1)
            if val[0].strip() != 'CommitTitle':
                print("Invalid file format.. CommitTitle not found..")
                print("Exiting..")
                exit()
            self.file_dict['tags']['CommitTitle'] = val[1].strip()

            # Store time as commit date
            line = fp.readline()
            if line.split()[0] != 'CommitDate:':
                print("Invalid file format.. Commit Date not found..")
                print("Exiting..")
                exit()
            self.file_dict['time'] = line.split()[1]

            # Store Total Defects
            line = fp.readline()
            val = line.split(':')
            if val[0].strip() != 'TotalDefects':
                print("Invalid file format.. TotalDefects not found..")
                print("Exiting..")
                exit()
            self.file_dict['fields']['TotalDefects'] = int(val[1].strip())

            # Store Mandatory Defects
            line = fp.readline()
            val = line.split(':')
            if val[0].strip() != 'MandatoryDefects':
                print("Invalid file format.. MandatoryDefects not found..")
                print("Exiting..")
                exit()
            self.file_dict['fields']['MandatoryDefects'] = int(val[1].strip())

            # Store Required Defects
            line = fp.readline()
            val = line.split(':')
            if val[0].strip() != 'RequiredDefects':
                print("Invalid file format.. RequiredDefects not found..")
                print("Exiting..")
                exit()
            self.file_dict['fields']['RequiredDefects'] = int(val[1].strip())

            # Store Advisory Defects
            line = fp.readline()
            val = line.split(':')
            if val[0].strip() != 'AdvisoryDefects':
                print("Invalid file format.. AdvisoryDefects not found..")
                print("Exiting..")
                exit()
            self.file_dict['fields']['AdvisoryDefects'] = int(val[1].strip())


def write_database(file_dict):
    misra_defects_data = {}
    misra_defects_data["data"] = []
    misra_defects_data["metadata"] = {}
    misra_defects_data["metadata"]["metrics"] = "tfa_misra_defects"
    misra_defects_data["api_version"] = "1.0"
    misra_defects_data["data"].append(file_dict)
    with open('tfa_misra_defects.json', 'w') as fp:
        json.dump(misra_defects_data, fp)


def get_tfa_coverity_file():
    # Create parser instance and add argument
    parser = argparse.ArgumentParser(
        description="TF-A quality metrics: Misra C defects tracking")
    parser.add_argument("--misra_defects_file",
                        help="file containing Misra defects information")

    # Parse the args
    args = parser.parse_args()

    # Check if file exists
    if os.path.isfile(str(args.misra_defects_file)):
        return args.misra_defects_file
    else:
        print("Coverity file not found.. Exiting..")
        exit()


if __name__ == '__main__':
    tfa_misra_defects_data = TFACoverityFileParser(
        str(get_tfa_coverity_file()))
    write_database(tfa_misra_defects_data.file_dict)
