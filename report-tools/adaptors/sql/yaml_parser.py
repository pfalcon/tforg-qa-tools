##############################################################################
# Copyright (c) 2021, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################
"""
Class to parse .yaml file to generate a report.db
"""
import sys
import yaml
import adaptors.sql.sqlite as sqlite

class YAMLParser:
    """
    Class to represent a YAML Parser and creates database

    Methods:
        create_table: Creates sqlite db table with necessary fields.
        parse_file: Parses the yaml file to obtain necessary data for the test result table and updates it.
        update_test_config_table: Parses the yaml file to obtain necessary data fot the test config table and updates it
    """
    root_string = ""
    test_suite_list = []

    # contents of the test_config table
    test_config_table = [
        "build_id",
        "target",
        "bitbake_version",
        "yocto_version"
    ]

    # contents of test_result table
    test_result_table = [
        "build_id",
        "date",
        "test_suite",
        "test_case",
        "result"
    ]

    def __init__(self, file_name=""):
        """Creates an instance for sqlite_obj and loads the contents of the yamlfile to be parsed """

        try:
            self.sqlite_obj = sqlite.Database("report.db")
            with open(file_name) as file:
                self.contents = yaml.load(file)
                self.root_string = [i for i in self.contents.keys()][0]
        except Exception as err:
            print(err)

    def create_table(self):
        """Creates empty tables in the sqlite database from the contents of test_config_table and test_result_table"""

        test_config_query = """
        CREATE TABLE `test_configuration` (
        {0} TEXT,
        {1} TEXT,
        {2} TEXT,
        {3} TEXT,
        PRIMARY KEY ({0})
        );
        """.format(self.test_config_table[0], self.test_config_table[1], self.test_config_table[2],
                   self.test_config_table[3])

        test_results_query = """
        CREATE TABLE `test_results` (
        {0} TEXT,
        {1} TEXT,
        {2} TEXT,
        {3} TEXT,
        {4} TEXT,
        FOREIGN KEY ({0}) REFERENCES `test_configuration`({0})
        );
        """.format(self.test_result_table[0], self.test_result_table[1], self.test_result_table[2],
                   self.test_result_table[3], self.test_result_table[4])

        self.sqlite_obj.execute_query(test_config_query)
        self.sqlite_obj.execute_query(test_results_query)

    def parse_file(self):
        """Parses the yaml file"""

        build_id = self.contents[self.root_string]['metadata']['CI_PIPELINE_ID']
        for test_suite in self.contents[self.root_string]['test-suites'].keys():
            date = self.contents[self.root_string]['test-suites'][test_suite]['metadata']['DATE']
            for test_case in self.contents[self.root_string]['test-suites'][test_suite]['test-results'].keys():
                result = self.contents[self.root_string]['test-suites'][test_suite]['test-results'][test_case]["status"]
                update_result_table_query = "INSERT INTO test_results VALUES ('{0}', '{1}', '{2}', '{3}', '{4}')". \
                    format(build_id, date, test_suite, test_case, result)
                self.sqlite_obj.execute_query(update_result_table_query)

    def update_test_config_table(self):
        """Updates tables in the report.db with the values from the yaml file"""

        build_id = self.contents[self.root_string]['metadata']['CI_PIPELINE_ID']
        target = self.contents[self.root_string]['target']['platform'] + \
            "_" + self.contents[self.root_string]['target']['version']

        bitbake_version = "UNAVAILABLE"
        yocto_version = "UNAVAILABLE"
        update_table_query = "INSERT INTO test_configuration VALUES ('{0}', '{1}', '{2}', '{3}')".\
            format(build_id, target, bitbake_version, yocto_version)
        self.sqlite_obj.execute_query(update_table_query)


if __name__ == "__main__":
    yaml_obj = YAMLParser()
    yaml_obj.create_table()
    yaml_obj.parse_file()
    yaml_obj.update_test_config_table()
 
