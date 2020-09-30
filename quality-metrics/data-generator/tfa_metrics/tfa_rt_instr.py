#!/usr/bin/env python

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" tfa_rt_instr.py:

       Parses the job output log file, stores the data in a list of dictionaries
       and creates JSON file to be written to influxDB.

       USAGE: python3 tfa_rt_instr.py --rt_instr <job_output.log>

   """

import argparse
import os
import os.path
import re
import json


class TFAInstrFileParser:
    dict_list = []
    file_name = None
    rtinstr_data = {}
    rtinstr_data["data"] = []
    rtinstr_data["metadata"] = {}
    rtinstr_data["metadata"]["metrics"] = "tfa_rtinstr"
    rtinstr_data["api_version"] = "1.0"

    def __init__(self, input_file):
        self.file_name = input_file
        self.parse_instr_file()
        print(json.dumps(self.dict_list, indent=4, sort_keys=True))

    def write_database_instr_tfa(self, file_dict):
        self.rtinstr_data["data"].append(file_dict)

    def parse_instr_file(self):
        with open(self.file_name) as fp:
            # Store instrumentation target as measurement name
            line = fp.readline()
            val = line.split(':')
            if val[0].strip() != 'InstrumentationTarget':
                print("Invalid file format.. Intrumentation not found..")
                print("Exiting..")
                exit()
            measurement = val[1].strip()

            # Store commit ID
            line = fp.readline()
            val = line.split(':')
            if val[0].strip() != 'CommitID':
                print("Invalid file format.. Commit ID not found..")
                print("Exiting..")
                exit()
            commit_id = val[1].strip()[0:10]

            # Store commit title
            line = fp.readline()
            val = line.split(':', 1)
            if val[0].strip() != 'CommitTitle':
                print("Invalid file format.. CommitTitle not found..")
                print("Exiting..")
                exit()
            commit_title = val[1].strip()

            # Store time as commit date
            line = fp.readline()
            if line.split()[0] != 'CommitDate:':
                print("Invalid file format.. Commit Date not found..")
                print("Exiting..")
                exit()
            commit_time = line.split()[1]

            # Store latency data per test case
            for line in iter(fp.readline, ''):
                file_dict = {}
                file_dict['tags'] = {}
                file_dict['fields'] = {}
                file_dict['measurement'] = measurement
                file_dict['tags']['CommitID'] = commit_id
                file_dict['tags']['CommitTitle'] = commit_title
                file_dict['time'] = commit_time
                tc_arr = line.split()
                file_dict['tags']['TC_Name'] = tc_arr[0]
                file_dict['tags']['Cluster_ID'] = int(tc_arr[1])
                file_dict['tags']['CPU_Core'] = int(tc_arr[2])
                if file_dict['tags']['TC_Name'] == 'testrtinstrpsciversionparallel':
                    file_dict['fields']['Latency_EL3Entry_EL3Exit'] = int(
                        tc_arr[3])
                else:
                    file_dict['fields']['Latency_EL3Entry_CPUPowerDown'] = int(
                        tc_arr[3])
                    file_dict['fields']['Latency_CPUWakeup_EL3Exit'] = int(
                        tc_arr[4])
                    file_dict['fields']['CacheFlush'] = int(tc_arr[5])
                self.write_database_instr_tfa(file_dict)

            with open('tfa_rtinstr.json', 'w') as fp:
                json.dump(self.rtinstr_data, fp)


def get_tfa_instr_file():
    # Create parser instance and add argument
    parser = argparse.ArgumentParser(
        description="TFA quality metrics: Runtime Instrumentation tracking")
    parser.add_argument(
        "--rt_instr",
        help="file containing TF-A runtime instrumentation info")

    # Parse the args
    args = parser.parse_args()

    # Check if file exists
    if os.path.isfile(str(args.rt_instr)):
        return args.rt_instr
    else:
        print("Runtime Instrumentation file not found.. Exiting..")
        exit()


if __name__ == '__main__':
    tfa_instr_file_data = TFAInstrFileParser(str(get_tfa_instr_file()))
