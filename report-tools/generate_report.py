##############################################################################

# Copyright (c) 2021, ARM Limited and Contributors. All rights reserved.

#

# SPDX-License-Identifier: BSD-3-Clause

##############################################################################
import re
import yaml
import argparse
import os
import logging
import subprocess
import sys
import json
from adaptors.sql.yaml_parser import YAMLParser
import glob

HTML_TEMPLATE = "html.tar.gz"


class TCReport(object):
    """
    Class definition for objects to build report files in a
    pipeline stage
    """
    STATUS_VALUES = ["PASS", "FAIL", "SKIP"]

    def __init__(self, metadata=None, test_environments=None,
                 test_configuration=None, target=None,
                 test_suites=None, report_file=None):
        """
        Constructor for the class. Initialise the report object and loads
        an existing report(yaml) if defined.

        :param metadata: Initial metadata report object
        :param test_environments: Initial test environment object
        :param test_configuration: Initial test configuration object
        :param target: Initial target object
        :param test_suites: Initial test suites object
        :param report_file: If defined then an existing yaml report is loaded
        as the initial report object
        """
        if test_suites is None:
            test_suites = {}
        if target is None:
            target = {}
        if test_configuration is None:
            test_configuration = {'test-assets': {}}
        if test_environments is None:
            test_environments = {}
        if metadata is None:
            metadata = {}
        self._report_name = "Not-defined"
        # Define if is a new report or an existing report
        if report_file:
            # The structure of the report must follow:
            # - report name:
            #               {report properties}
            try:
                with open(report_file) as f:
                    full_report = yaml.load(f)
                    self._report_name, \
                    self.report = list(full_report.items())[0]
            except Exception as ex:
                logging.exception(
                    f"Exception loading existing report '{report_file}'")
                raise ex
        else:
            self.report = {'metadata': metadata,
                           'test-environments': test_environments,
                           'test-config': test_configuration,
                           'target': target,
                           'test-suites': test_suites
                           }
        self.report_file = report_file

    def dump(self, file_name):
        """
        Method that dumps the report object with the report name as key in
        a yaml format in a given file.

        :param file_name: File name to dump the yaml report
        :return: Nothing
        """
        with open(file_name, 'w') as f:
            yaml.dump({self._report_name: self.report}, f)

    @property
    def test_suites(self):
        return self.report['test-suites']

    @test_suites.setter
    def test_suites(self, value):
        self.test_suites = value

    @property
    def test_environments(self):
        return self.report['test-environments']

    @test_environments.setter
    def test_environments(self, value):
        self.test_environments = value

    @property
    def test_config(self):
        return self.report['test-config']

    @test_config.setter
    def test_config(self, value):
        self.test_config = value

    def add_test_suite(self, name: str, test_results, metadata=None):
        """
        Public method to add a test suite object to a report object.

        :param name: Unique test suite name
        :param test_results: Object with the tests results
        :param metadata: Metadata object for the test suite
        """
        if metadata is None:
            metadata = {}
        if name in self.test_suites:
            logging.error("Duplicated test suite:{}".format(name))
        else:
            self.test_suites[name] = {'test-results': test_results,
                                      'metadata': metadata}

    def add_test_environment(self, name: str, values=None):
        """
        Public method to add a test environment object to a report object.

        :param name: Name (key) of the test environment object
        :param values: Object assigned to the test environment object
        :return: Nothing
        """
        if values is None:
            values = {}
        self.test_environments[name] = values

    def add_test_asset(self, name: str, values=None):
        """
        Public method to add a test asset object to a report object.

        :param name: Name (key) of the test asset object
        :param values: Object assigned to the test asset object
        :return: Nothing
        """
        if values is None:
            values = {}
        if 'test-assets' not in self.test_config:
            self.test_config['test-assets'] = {}
        self.test_config['test-assets'][name] = values

    @staticmethod
    def process_ptest_results(lava_log_string="",
                              results_pattern=r"(?P<status>("
                                              r"PASS|FAIL|SKIP)): ("
                                              r"?P<id>.+)"):
        """
        Method that process ptest-runner results from a lava log string and
        converts them to a test results object.

        :param lava_log_string: Lava log string
        :param results_pattern: Regex used to capture the test results
        :return: Test results object
        """
        pattern = re.compile(results_pattern)
        if 'status' not in pattern.groupindex or \
            'id' not in pattern.groupindex:
            raise Exception(
                "Status and/or id must be defined in the results pattern")
        results = {}
        lines = lava_log_string.split("\n")
        it = iter(lines)
        stop_found = False
        for line in it:
            fields = line.split(" ", 1)
            if len(fields) > 1 and fields[1] == "START: ptest-runner":
                for report_line in it:
                    timestamp, *rest = report_line.split(" ", 1)
                    if not rest:
                        continue
                    if rest[0] == "STOP: ptest-runner":
                        stop_found = True
                        break
                    p = pattern.match(rest[0])
                    if p:
                        id = re.sub("[ :]+", "_", p.groupdict()['id'])
                        status = p.groupdict()['status']
                        if not id:
                            print("Warning: missing 'id'")
                        elif status not in TCReport.STATUS_VALUES:
                            print("Warning: Status unknown")
                        elif id in results:
                            print("Warning: duplicated id")
                        else:
                            metadata = {k: p.groupdict()[k]
                                        for k in p.groupdict().keys()
                                        if k not in ('id', 'status')}
                            results[id] = {'status': status,
                                           'metadata': metadata}
                break
        if not stop_found:
            logger.warning("End of ptest-runner not found")
        return results

    def parse_fvp_model_version(self, lava_log_string):
        """
        Obtains the FVP model and version from a lava log string.

        :param lava_log_string: Lava log string
        :return: Tuple with FVP model and version
        """
        result = re.findall(r"opt/model/(.+) --version", lava_log_string)
        model = "" if not result else result[0]
        result = re.findall(r"Fast Models \[(.+?)\]\n", lava_log_string)
        version = "" if not result else result[0]
        self.report['target'] = {'platform': model, 'version': version}
        return model, version

    @property
    def report_name(self):
        return self._report_name

    @report_name.setter
    def report_name(self, value):
        self._report_name = value

    @property
    def metadata(self):
        return self.report['metadata']

    @metadata.setter
    def metadata(self, metadata):
        self.report['metadata'] = metadata

    @property
    def target(self):
        return self.report['target']

    @target.setter
    def target(self, target):
        self.report['target'] = target

    def merge_into(self, other):
        """
        Merge one report object with this.

        :param other: Report object to be merged to this
        :return:
        """
        try:
            if not self.report_name or self.report_name == "Not-defined":
                self.report_name = other.report_name
            if self.report_name != other.report_name:
                logging.warning(
                    f'Report name \'{other.report_name}\' does not match '
                    f'original report name')
                # Merge metadata where 'other' report will overwrite common key
            # values
            self.metadata.update(other.metadata)
            self.target.update(other.target)
            self.test_config['test-assets'].update(other.test_config['test'
                                                                     '-assets'])
            self.test_environments.update(other.test_environments)
            self.test_suites.update(other.test_suites)
        except Exception as ex:
            logging.exception("Failed to merge reports")
            raise ex
            

class KvDictAppendAction(argparse.Action):
    """
    argparse action to split an argument into KEY=VALUE form
    on the first = and append to a dictionary.
    """

    def __call__(self, parser, args, values, option_string=None):
        d = getattr(args, self.dest) or {}
        for value in values:
            try:
                (k, v) = value.split("=", 2)
            except ValueError as ex:
                raise \
                    argparse.ArgumentError(self,
                                           f"Could not parse argument '{values[0]}' as k=v format")
            d[k] = v
        setattr(args, self.dest, d)


def read_metadata(metadata_file):
    """
    Function that returns a dictionary object from a KEY=VALUE lines file.

    :param metadata_file: Filename with the KEY=VALUE pairs
    :return: Dictionary object with key and value pairs
    """
    if not metadata_file:
        return {}
    with open(metadata_file) as f:
        d = dict([line.strip().split("=", 1) for line in f])
    return d


def import_env(env_names):
    """
    Function that matches a list of regex expressions against all the
    environment variables keys and returns an object with the matched key
    and the value of the environment variable.

    :param env_names: List of regex expressions to match env keys
    :return: Object with the matched env variables
    """
    env_list = list(os.environ.keys())
    keys = []
    for expression in env_names:
        r = re.compile(expression)
        keys = keys + list(filter(r.match, env_list))
    d = {key: os.environ[key] for key in keys}
    return d


def merge_dicts(*dicts):
    """
    Function to merge a list of dictionaries.

    :param dicts: List of dictionaries
    :return: A merged dictionary
    """
    merged = {}
    for d in dicts:
        merged.update(d)
    return merged


def process_lava_log(_report, _args):
    """
    Function to adapt user arguments to process test results and add properties
    to the report object.

    :param _report: Report object
    :param _args: User arguments
    :return: Nothing
    """
    with open(_args.lava_log, "r") as f:
        lava_log = f.read()
    # Get the test results
    results = {}
    if _args.type == 'ptest-report':
        results_pattern = None
        suite = _args.suite or _args.test_suite_name
        if suite == "optee-test":
            results_pattern = r"(?P<status>(PASS|FAIL|SKIP)): (?P<id>.+ .+) " \
                              r"- (?P<description>.+)"
        elif suite == "kernel-selftest":
            results_pattern = r"(?P<status>(PASS|FAIL|SKIP)): (" \
                              r"?P<description>selftests): (?P<id>.+: .+)"
        else:
            logging.error(f"Suite type uknown or not defined:'{suite}'")
            sys.exit(-1)

        results = TCReport.process_ptest_results(lava_log,
                                                 results_pattern=results_pattern)
    if _args.report_name:
        _report.report_name = _args.report_name
    _report.parse_fvp_model_version(lava_log)
    metadata = {}
    if _args.metadata_pairs or _args.metadata_env or _args.metadata_file:
        metadata = _args.metadata_pairs or import_env(
            _args.metadata_env) or read_metadata(_args.metadata_file)
    _report.add_test_suite(_args.test_suite_name, test_results=results,
                           metadata=metadata)


def merge_reports(reportObj, list_reports):
    """
    Function to merge a list of yaml report files into a report object

    :param reportObj: Instance of an initial report object to merge the reports
    :param list_reports: List of yaml report files or file patterns
    :return: Updated report object
    """
    for report_pattern in list_reports:
        for report_file in glob.glob(report_pattern):
            to_merge = TCReport(report_file=report_file)
            reportObj.merge_into(to_merge)
    return reportObj


def generate_html(report_obj, user_args):
    """
    Generate html output for the given report_file

    :param report_obj: report object
    :param user_args: Arguments from user
    :return: Nothing
    """
    script_path = os.path.dirname(sys.argv[0])
    report_file = user_args.report
    try:
        with open(script_path + "/html/js/reporter.js", "a") as write_file:
            for key in args.html_output:
                print(f'\nSetting html var "{key}"...')
                write_file.write(f"\nlet {key}='{args.html_output[key]}'")
            j = json.dumps({report_obj.report_name: report_obj.report},
                           indent=4)
            write_file.write(f"\nlet textReport=`\n{j}\n`")
        subprocess.run(f'cp -f {report_file} {script_path}/html/report.yaml',
                       shell=True)
    except subprocess.CalledProcessError as ex:
        logging.exception("Error at generating html")
        raise ex


if __name__ == '__main__':
    # Defining logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("debug.log"),
            logging.StreamHandler()
        ])
    """
    The main aim of this script is to be called with different options to build
    a report object that can be dumped into a yaml format
    """
    parser = argparse.ArgumentParser(description='Generic yaml report for TC')
    parser.add_argument("--report", "-r", help="Report filename")
    parser.add_argument("-f", help="Force new report", action='store_true',
                        dest='new_report')
    parser.add_argument("command", help="Command: process-results")
    group_results = parser.add_argument_group("Process results")
    group_results.add_argument('--test-suite-name', type=str,
                               help='Test suite name')
    group_results.add_argument('--lava-log', type=str, help='Lava log file')
    group_results.add_argument('--type', type=str, help='Type of report log',
                               default='ptest-report')
    group_results.add_argument('--report-name', type=str, help='Report name',
                               default="")
    group_results.add_argument("--suite", required=False,
                               default=None,
                               help="Suite type. If not defined takes the "
                                    "suite name value")
    test_env = parser.add_argument_group("Test environments")
    test_env.add_argument('--test-env-name', type=str,
                          help='Test environment type')
    test_env.add_argument("--test-env-values",
                          nargs="+",
                          action=KvDictAppendAction,
                          default={},
                          metavar="KEY=VALUE",
                          help="Set a number of key-value pairs "
                               "(do not put spaces before or after the = "
                               "sign). "
                               "If a value contains spaces, you should define "
                               "it with double quotes: "
                               'key="Value with spaces". Note that '
                               "values are always treated as strings.")
    test_env.add_argument("--test-env-env",
                          nargs="+",
                          default={},
                          help="Import environment variables values with the "
                               "given name.")
    parser.add_argument("--metadata-pairs",
                        nargs="+",
                        action=KvDictAppendAction,
                        default={},
                        metavar="KEY=VALUE",
                        help="Set a number of key-value pairs "
                             "(do not put spaces before or after the = sign). "
                             "If a value contains spaces, you should define "
                             "it with double quotes: "
                             'key="Value with spaces". Note that '
                             "values are always treated as strings.")

    test_config = parser.add_argument_group("Test config")
    test_config.add_argument('--test-asset-name', type=str,
                             help='Test asset type')
    test_config.add_argument("--test-asset-values",
                             nargs="+",
                             action=KvDictAppendAction,
                             default={},
                             metavar="KEY=VALUE",
                             help="Set a number of key-value pairs "
                                  "(do not put spaces before or after the = "
                                  "sign). "
                                  "If a value contains spaces, you should "
                                  "define "
                                  "it with double quotes: "
                                  'key="Value with spaces". Note that '
                                  "values are always treated as strings.")
    test_config.add_argument("--test-asset-env",
                             nargs="+",
                             default=None,
                             help="Import environment variables values with "
                                  "the given name.")

    parser.add_argument("--metadata-env",
                        nargs="+",
                        default=None,
                        help="Import environment variables values with the "
                             "given name.")
    parser.add_argument("--metadata-file",
                        type=str,
                        default=None,
                        help="File with key-value pairs lines i.e"
                             "key1=value1\nkey2=value2")
                             
    parser.add_argument("--list",
                        nargs="+",
                        default={},
                        help="List of report files.")
    parser.add_argument("--html-output",
                        required=False,
                        nargs="*",
                        action=KvDictAppendAction,
                        default={},
                        metavar="KEY=VALUE",
                        help="Set a number of key-value pairs i.e. key=value"
                             "(do not put spaces before or after the = "
                             "sign). "
                             "If a value contains spaces, you should define "
                             "it with double quotes: "
                             "Valid keys: title, logo_img, logo_href.")
    parser.add_argument("--sql-output",
                        required=False,
                        action="store_true",
                        help='Sql output produced from the report file')

    args = parser.parse_args()
    report = None

    # Check if report exists (that can be overwritten) or is a new report
    if os.path.exists(args.report) and not args.new_report:
        report = TCReport(report_file=args.report)  # load existing report
    else:
        report = TCReport()

    # Possible list of commands:
    # process-results: To parse test results from stream into a test suite obj
    if args.command == "process-results":
        # Requires the test suite name and the log file, lava by the time being
        if not args.test_suite_name:
            parser.error("Test suite name required")
        elif not args.lava_log:
            parser.error("Lava log file required")
        process_lava_log(report, args)
    # set-report-metadata: Set the report's metadata
    elif args.command == "set-report-metadata":
        # Various options to load metadata into the report object
        report.metadata = merge_dicts(args.metadata_pairs,
                                      read_metadata(args.metadata_file),
                                      import_env(args.metadata_env))
    # add-test-environment: Add a test environment to the report's object
    elif args.command == "add-test-environment":
        # Various options to load environment data into the report object
        report.add_test_environment(args.test_env_name,
                                    merge_dicts(args.test_env_values,
                                                import_env(args.test_env_env)))
    # add-test-asset: Add a test asset into the report's object (test-config)
    elif args.command == "add-test-asset":
        report.add_test_asset(args.test_asset_name,
                              merge_dicts(args.test_asset_values,
                                          import_env(args.test_asset_env)))
    elif args.command == "merge-reports":
        report = merge_reports(report, args.list)
    report.dump(args.report)
    if args.html_output:
        generate_html(report, args)

    if args.sql_output:
        yaml_obj = YAMLParser(args.report)
        yaml_obj.create_table()
        yaml_obj.parse_file()
        yaml_obj.update_test_config_table()
