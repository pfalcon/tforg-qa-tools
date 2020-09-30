#!/usr/bin/env python3

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" complexity_parser.py:

    Data converter class. This class is aimed at converting the received
    data in the format which InfluxDB understands.

"""

import collections
import re
import sys


class ComplexityParser(object):
    """
        Extract the following data from the complexity logs:
            - complexity table: {filename: <complexity score>}
    """

    def __init__(self, complexityLog, threshold):
        """ class constructor function """
        self.complexityLog = complexityLog
        self.complexityDict = collections.OrderedDict()
        self.threshold = threshold

        self.process_complexity_log()
        self.process_complexity_data()

    def process_complexity_log(self):
        """ function to process complexity log and populate the complexity dictionary """
        with open(self.complexityLog) as fp:
            for line in fp:
                scoreRegex = r"([0-9]+)\s+[0-9]+\s+[0-9]+\s+[0-9]+\s+[0-9]+\s+(.*)"
                m = re.match(scoreRegex, line)

                if m:
                    score = m.group(1)

                    self.complexityDict[m.group(2).strip()] = score

    def process_complexity_data(self):
        """ function to extract the function IDs above the complexity threshold """
        self.complexityDict = collections.OrderedDict(
            (k, v) for k, v in self.complexityDict.items() if int(v) >= self.threshold)

    def apply_whitelist(self):
        """ Add an additional field to indicate whitelist YES/NO """
        tmpDict = collections.OrderedDict()
        exclusionDict = collections.OrderedDict()

        # read in the whitelist
        with open('./whitelist.dat') as f:
            lines = f.read().splitlines()

        # construct a dictionary for the white list to deal with:
        # FULL_DIR_FOR_EXCLUSION, FULL_FILE_FOR_EXCLUSION and function
        for i in lines:
            tmpK = i.split(':')[0]
            tmpV = i.split(':')[1]
            exclusionDict[tmpK] = tmpV

        whitelist_match = 0

        for k, v in self.complexityDict.items():
            # dealing with whitelist
            for wlK, wlV in exclusionDict.items():

                if (wlV == "FULL_DIR_FOR_EXCLUSION") or (
                        wlV == "FULL_FILE_FOR_EXCLUSION"):
                    # dealing with FULL_DIR_EXCLUSION and FULL_FILE_FOR_EXCLUSION, here we compare the directory path name or
                    # file name before the ':'
                    if wlK in k.split(':')[0]:
                        whitelist_match = 1
                else:
                    # dealing with function exclusion
                    if wlV in k.split(':')[1]:
                        whitelist_match = 1

            if whitelist_match != 1:
                newValue = v + ",NO"
            else:
                newValue = v + ",YES"

            # add into the dictionary
            tmpDict[k] = newValue

            whitelist_match = 0

        return tmpDict


class ComplexityHTMLCreator(object):
    """
        Create HTML using the defect statistics
    """

    def __init__(self, complexityDict, fileName):
        """ Class constructor function """
        self.complexityDict = complexityDict
        # output file name
        self.fileName = fileName

        self.create_template_head()
        self.add_table_content()
        self.create_template_tail()

    def create_template_head(self):
        """ Function to make the HTML template """
        with open(self.fileName, 'w') as f:
            f.write("<!DOCTYPE html>\n")
            f.write("<html>\n")
            f.write("<head>\n")
            f.write("<style>\n")
            f.write("table, th, td{\n")
            f.write("    border: 1px solid black;\n")
            f.write("    border-collapse: collapse;\n")
            f.write("}\n")
            f.write("</style>\n")
            f.write("</head>\n")
            f.write("<body>\n")
            f.write("<table>\n")
            f.write("  <tr>\n")
            f.write("    <th>Function ID</th>\n")
            f.write("    <th>In-file location</th>\n")
            f.write("    <th>Complexity Score</th>\n")
            f.write("  </tr>\n")

    def add_table_content(self):
        """ function to add rows for test case result summary """
        with open(self.fileName, "a") as f:

            for functionInfo, score in self.complexityDict.items():
                if int(score) >= 10:
                    f.write("  <tr bgcolor=\"#E67E62\">\n")
                else:
                    f.write("  <tr>\n")

                # add function information
                location = functionInfo.split(':')[0].strip()
                functionName = functionInfo.split(':', 1)[1].strip()

                # add complexity score
                f.write("    <td>{0}</td>\n".format(functionName))
                f.write("    <td>{0}</td>\n".format(location))
                f.write("    <td>{0}</td>\n".format(score))
                f.write("  </tr>\n")

    def create_template_tail(self):
        """ function to add the closing part of html """

        with open(self.fileName, "a") as f:
            f.write("</table>\n")
            f.write("</body>\n")
            f.write("</html>\n")
