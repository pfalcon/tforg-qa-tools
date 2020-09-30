#!/usr/bin/env python

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" tfa_track_image_size.py:

       Parses TFA firmware image size file, stores the data in a list of
       dictionaries and creates JSON file to be written to influxDB.

       USAGE: python3 tfa_track_image_size.py --image_size_file <ImageSizeFil.txte>

   """

import argparse
import os.path
import re
import json

# Validation Variables
MEM_SECTION_VALIDATION_TABLE = ['B', 'D', 'R', 'T', 'V', 'W']
ELF_FILES_LOOKUP_TABLE = [
    'bl1.elf',
    'bl1u.elf',
    'bl2.elf',
    'bl2u.elf',
    'bl31.elf',
    'bl32.elf']


class TFASizeFileParser:
    """
        Download the file containing sizes of various TFA build configs
        Store the size data in a list of dictionaries in the following format:
            [
                {
                    "measurement": <build_config>,
                    "fields" : {
                        "BlX_B": Size of uninitialized data section
                        "BlX_D": Size of initialized data section
                        "BlX_R": Size of read only data section
                        "BlX_T": Size of text (code) section
                        "BlX_V": Size of weak object
                        "BlX_W": Size of weak symbol
                    },
                    "tags" : {
                        "BinMode"         : Type of build (Release|Debug)
                        "CommitID"        : Commit ID
                        "CommitTitle"     : Commit title
                    }
                    "time" : Commit Time
                }
            ]
    """

    file_dict = {}
    file_name = None

    def __init__(self, input_file):
        self.file_name = input_file
        self.parse_image_size_file()
        print(json.dumps(self.file_dict, indent=4, sort_keys=True))

    def parse_image_size_file(self):
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

            # Store Image Size memory related data component-wise
            for line in iter(fp.readline, ''):
                if ".elf" in line:
                    searched_build = line.split('/')[-1].split(':')[0]
                    build = searched_build.upper().rsplit('.', 1)[0]
                    if searched_build not in ELF_FILES_LOOKUP_TABLE:
                        print(
                            "WARNING: " +
                            searched_build +
                            " not present in ELF_FILES_LOOKUP_TABLE..")
                        print(
                            "Skipping publishing data for " +
                            searched_build +
                            " to InfluxDB")
                        build = None
                        continue
                elif build is not None:
                    val = line.split(' ')
                    if len(val) > 1:
                        if not val[0].strip() in MEM_SECTION_VALIDATION_TABLE:
                            print(
                                "Invalid memory section \"%s\".. Exiting.." %
                                val[0].strip())
                            exit()
                        mem_comp = build + "_" + val[0].strip()
                        self.file_dict['fields'][mem_comp] = int(
                            val[1].strip())

            json_body = json.dumps(str(self.file_dict))
            if not self.file_dict['fields']:
                failed_configs = 'failed_configs.txt'

                if os.path.exists(failed_configs):
                    append_write = 'a'  # append if already exists
                else:
                    append_write = 'w'  # make a new file if not

                failed_configs_file = open(failed_configs, append_write)
                failed_configs_file.write(
                    self.file_dict['measurement'] +
                    ', ' +
                    self.file_dict['tags']['BinMode'] +
                    ': bl1/bl1u/bl2/bl2u/bl31/bl32 not found\n')
                failed_configs_file.close()
                print("No memory section found.. Exiting")
                exit()


def generate_influxdb_json_file(file_dict):
    image_size_data = {}
    image_size_data["data"] = []
    image_size_data["metadata"] = {}
    image_size_data["metadata"]["metrics"] = "tfa_image_size"
    image_size_data["api_version"] = "1.0"
    image_size_data["data"].append(file_dict)
    with open('tfa_image_size.json', 'w') as fp:
        json.dump(image_size_data, fp)


def get_tfa_size_file():
    # Create parser instance and add argument
    parser = argparse.ArgumentParser(
        description="TFA quality metrics: firmware image size tracking")
    parser.add_argument(
        "--image_size_file",
        help="file containing TFA image size info")

    # Parse the args
    args = parser.parse_args()

    # Check if file exists
    if os.path.isfile(str(args.image_size_file)):
        return args.image_size_file
    else:
        print("Image size file not found.. Exiting..")
        exit()


if __name__ == '__main__':
    tfa_size_file_data = TFASizeFileParser(str(get_tfa_size_file()))
    generate_influxdb_json_file(tfa_size_file_data.file_dict)
