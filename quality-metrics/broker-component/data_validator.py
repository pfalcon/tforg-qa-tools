#!/usr/bin/env python3

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" data_validator.py:

    JSON data validator class. This class is aimed at validating the JSON
    data sent in curl command with the JSON schema, so that before pushing
    the data to the database, it is ensured that required data is received
    in agreed-upon format.

"""

import sys
import json
import os.path
import constants
import jsonschema
from jsonschema import validate


class DataValidator:
    @staticmethod
    def validate_request_sanity(data_dict):
        """
            Input sanitisation/authentication in the application flow

            :param: data_dict: Data to be validated
            :return: Validation info and error code
        """
        if 'metrics' in data_dict['metadata'] and 'api_version' in data_dict and \
                data_dict['metadata']['metrics'] in constants.VALID_METRICS:
            if data_dict['api_version'] not in constants.SUPPORTED_API_VERSIONS:
                return 'Incorrect API version', 401

            filename = 'metrics-schemas/' + data_dict['metadata']['metrics'] + '_schema_' + \
                data_dict['api_version'].replace(".", "_") + '.json'
            if not os.path.exists(filename):
                return filename + ' does not exist', 501

            try:
                with open(filename, 'r') as handle:
                    parsed = json.load(handle)
                validate(data_dict, parsed)
                sys.stdout.write('Record OK\n')
                return 'OK', 204
            except jsonschema.exceptions.ValidationError as ve:
                sys.stdout.write('Record ERROR\n')
                sys.stderr.write(str(ve) + "\n")
                return 'Incorrect JSON Schema: ' + \
                    str(ve).split('\n', 1)[0], 400
        else:
            return 'Invalid schema - metrics or api version missing\n', 401
