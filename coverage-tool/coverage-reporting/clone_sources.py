# !/usr/bin/env python
###############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################

###############################################################################
# FILE: clone_sources.py
#
# DESCRIPTION: Clone the source files for code coverage
###############################################################################

import os
import subprocess
import json
import time
from random import random


def call_cmd(cmd, print_cmd=False):
    """
    Function that execute an os command and returns its output

    :param cmd: OS command as string
    :param print_cmd: Optional argument to print the command in stdout
    :return: The string output of the os command
    """
    if print_cmd:
        print("+" + cmd)
    out = subprocess.check_output(cmd, shell=True)
    return out


def skip_source(output_dir, source, handler=None):
    """
    Function that handles overwriting source files

    :param output_dir: Folder where to put the source files and folders
    :param source: Dictionary with the information the source
    :return: True if must skip the given source cloning False otherwise
    """
    location = os.path.join(output_dir, source['LOCATION'])
    # Check if exists and have files
    if os.path.isdir(location):
        if not os.listdir(location):
            if handler is not None:
                return handler(source, "Directory exists and is empty")
            else:
                # By default send a warning and overwrite it
                print(("WARNING!: Directory {} already exists and is "
                       "empty. Overwriting it...'").format(location))
                os.rmdir(location)
                return False
        commit_id = call_cmd(("cd {} && git log -1 2>/dev/null | "
                              "grep commit | awk '{{print $2}}'").format(
                              location), print_cmd=True).strip()
        if source['type'] == "git":
            if commit_id == "":
                # is not a git
                if handler is not None:
                    return handler(source, "Directory exists and is not git")
                else:
                    print(("WARNING!: Directory {} already exists and is not a"
                           " git repo: '{}'").format(location, source['URL']))
            elif commit_id != source["COMMIT"].strip():
                # there are mismatching commit id's
                if handler is not None:
                    return handler(source, "Mismatch in gits")
                else:
                    print(("WARNING!: Mismatch in git repo {}\nExpected {}, "
                           "Cloned {}").format(source['URL'], source['COMMIT'],
                                               commit_id))
        elif source['type'] == "http":
            if handler is not None:
                return handler(source,
                               "WARNING!: Directory already exists")
            else:
                print("WARNING!: Directory {} already exists".format(
                    location))
        return True
    return False


class CloneSources(object):
    """Class used to clone the source code needed to produce code coverage
    reports.
    """
    def __init__(self, json_file):
        self.json_file = json_file
        self.json_data = None
        self.load_json()

    def load_json(self):
        with open(self.json_file, "r") as json_file:
            self.json_data = json.load(json_file)

    def clone_repo(self, output_dir, overwrite_handler=None):
        """
        Clones or reproduces a folder with source code based in the
        configuration in the json file

        :param output_dir: Where to put the source files
        :param overwrite_handler: Optional function to handle overwrites
        """
        if self.json_data is None:
            self.load_json()
        sources = []
        try:
            if 'parameters' in self.json_data:
                sources = self.json_data['parameters']['sources']
            elif 'configuration' in self.json_data:
                sources = self.json_data['configuration']['sources']
            else:
                raise Exception("No correct format for json sources!")
        except Exception as ex:
            raise Exception(ex)

        for source in sources:
            if skip_source(output_dir, source, overwrite_handler):
                continue
            if source['type'] == "git":
                git = source
                url = git["URL"]
                commit_id = git["COMMIT"]
                output_loc = os.path.join(output_dir, git["LOCATION"])
                cmd = "git clone {} {}".format(url, output_loc)
                output = call_cmd(cmd)
                if git['REFSPEC']:
                    call_cmd("cd {};git fetch -q origin {}".format(
                        output_loc, git['REFSPEC']))
                if commit_id:
                    call_cmd("cd {};git checkout -q {}".format(
                        output_loc, commit_id))
                else:
                    call_cmd("cd {};git checkout -q FETCH_HEAD".format(
                        output_loc))
            elif source['type'] == 'http':
                site = source
                output_loc = os.path.join(output_dir, site["LOCATION"])
                tmp_folder = os.path.join(output_dir,
                                          "_tmp_{}_{}".format(time.time(),
                                                              random()))
                call_cmd("mkdir -p {}".format(tmp_folder))
                call_cmd("wget -q {} -P {}".format(
                    site['URL'], tmp_folder))
                call_cmd("mkdir -p {}".format(output_loc))
                if site['COMPRESSION'] == "xz":
                    call_cmd("cd {};tar -xzf $(basename {}) -C {}".format(
                        tmp_folder, site['URL'], output_loc))
                call_cmd("rm -rf {}".format(tmp_folder))
