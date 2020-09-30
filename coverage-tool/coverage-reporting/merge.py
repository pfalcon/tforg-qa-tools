# !/usr/bin/env python
###############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################

###############################################################################
# FILE: merge.py
#
# DESCRIPTION: Merge two or more .info and json files, sanitizing source file
#              paths.
#              If different .info files contain the same source code duplicated
#              in different directories, we use the absolute paths of the
#              first .info file.
#
###############################################################################


import os
import sys
import argparse
from argparse import RawTextHelpFormatter
import subprocess
import json


# Define an argument parser using the argparse library
parser = argparse.ArgumentParser(epilog="""Example of usage:
python3 merge.py -a coverage_1.info -a coverage_2.info -o coverage_merge.info \
-j input_file1.json -j input_file2.json -m merge_file.json

It is possible to merge any number of files at once.
If metadata json files are defined then they must pair with their
corresponding info file, i.e. have the same name.
If a local workspace is defined then the paths in the info files will
be translated from the original test workspace to the local workspace
to enable the usage of LCOV, but the original files will be kept intact.
By default, the output file must be a new file.
To overwrite an existing file, use the "--force" option.

Note: the user is expected to merge .info files referring to the same project.
If merging .info files from different projects, LCOV can be exploited directly
using a command such as "lcov -rc lcov_branch_coverage=1 -a coverage_1.info \
-a coverage_2.info -o coverage_merge.info."
""", formatter_class=RawTextHelpFormatter)
requiredNamed = parser.add_argument_group('required named arguments')
requiredNamed.add_argument("-a", "--add-file",
                           help="Input info file to be merged.",
                           action='append', required=True)
requiredNamed.add_argument("-o", "--output",
                           help="Name of the output info (merged) file.",
                           required=False)
parser.add_argument("-j", "--json-file", action='append',
                    help="Input json file to be merged.")
parser.add_argument("-m", "--output-json",
                    help="Name of the output json (merged) file.")
parser.add_argument("--force", dest='force', action='store_true',
                    help="force overwriting of output file.")
parser.add_argument("--local-workspace", dest='local_workspace',
                    help='Local workspace where source files reside.')

options = parser.parse_args(sys.argv[1:])
# At least two .info files are expected
if len(options.add_file) < 2:
    print('Error: too few input files.\n')
    sys.exit(1)
# The same number of info and json files expected
if options.json_file:
    if len(options.json_file) != len(options.add_file):
        print('Umatched number of info and json files.\n')
        sys.exit(1)

file_groups = []
info_files_to_merge = []
# Check if files exist
for file_name in options.add_file:
    print("Merging '{}'".format(file_name))
    if not os.path.isfile(file_name):
        print('Error: file "' + file_name + '" not found.\n')
        sys.exit(1)
    if not file_name[-5:] == '.info':
        print('Error: file "' + file_name +
              '" has wrong extension. Expected .info file.\n')
        sys.exit(1)
    if file_name in info_files_to_merge:
        print("Error: Duplicated info file '{}'".format(file_name))
        sys.exit(1)
    info_files_to_merge.append(file_name)
    file_group = {"info": file_name, "locations": [], "json": ""}
    info_name = os.path.basename(file_name).split(".")[0]
    if options.json_file:
        json_name = [i for i in options.json_file
                     if os.path.basename(i).split(".")[0] == info_name]
        if not json_name:
            print("Umatched json file name for '{}'".format(file_name))
            sys.exit(1)
        json_name = json_name.pop()
        if not json_name[-5:] == '.json':
            print('Error: file "' + json_name +
                  '" has wrong extension. Expected .json file.\n')
            sys.exit(1)
        if not os.path.isfile(json_name):
            print('Error: file "' + json_name + '" not found.\n')
            sys.exit(1)
        # Now we have to extract the location folders for each info
        # this is needed if we want translation to local workspace
        file_group["json"] = json_name
        with open(json_name) as json_file:
            json_data = json.load(json_file)
        locations = []
        for source in json_data["configuration"]["sources"]:
            locations.append(source["LOCATION"])
        file_group["locations"] = locations
    file_groups.append(file_group)

# Check the extension of the output file
if not options.output[-5:] == '.info':
    print('Error: file "' + options.output +
          '" has wrong extension. Expected .info file.\n')
    sys.exit(1)

if options.local_workspace is not None:
    # Translation from test to local workspace
    i = 0
    while i < len(info_files_to_merge):
        info_file = open(info_files_to_merge[i], "r")
        print("Translating workspace for '{}'...".format(
              info_files_to_merge[i]))
        info_lines = info_file.readlines()
        info_file.close()
        common_prefix = os.path.normpath(
            os.path.commonprefix([line[3:] for line in info_lines
                                  if 'SF:' in line]))
        temp_file = 'temporary_' + str(i) + '.info'
        with open(temp_file, "w+") as f:
            for line in info_lines:
                cf = common_prefix
                if os.path.basename(common_prefix) in file_groups[i]["locations"]:
                    cf = os.path.dirname(common_prefix)
                f.write(line.replace(cf, options.local_workspace))
        info_files_to_merge[i] = temp_file  # Replace info file to be merged
        i += 1

# Merge json files
if len(options.json_file):
    json_merged_list = []
    json_merged = {}
    j = 0
    while j < len(options.json_file):
        json_file = options.json_file[j]
        with open(json_file) as f:
            data = json.load(f)
        for source in data['configuration']['sources']:
            if source not in json_merged_list:
                json_merged_list.append(source)
        j += 1
    json_merged = {'configuration': {'sources': json_merged_list}}
    with open(options.output_json, 'w') as f:
        json.dump(json_merged, f)


# Exploit LCOV merging capabilities
# Example of LCOV usage: lcov -rc lcov_branch_coverage=1 -a coverage_1.info \
# -a coverage_2.info -o coverage_merge.info
command = ['lcov', '-rc', 'lcov_branch_coverage=1']

for file_name in info_files_to_merge:
    command.append('-a')
    command.append(file_name)
command.append('-o')
command.append(options.output)

subprocess.call(command)

# Delete the temporary files
if options.local_workspace is not None:
    for f in info_files_to_merge:
        os.remove(f)
