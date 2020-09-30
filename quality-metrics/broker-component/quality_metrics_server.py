#!/usr/bin/env python3

from __future__ import print_function
from data_validator import DataValidator
import credentials

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" quality_metrics_server.py:

    This is the broker component which accepts the data from data
    generator scripts, and performs basic sanity check and pushes
    the data to Influx-DB for visualisation with Grafana component.
    It is not mandatory to push data via data generator scripts.
    The request to push data to database, in this case - InfluxDB,
    is expected to be be a POST request with right credentials and
    should be in agreed upon format.

"""

from pprint import pprint
from pprint import pformat
from db_manager import dbManager
from flask_jwt import JWT, jwt_required
from flask import Flask, jsonify, request
from werkzeug.security import safe_str_cmp
from logging.handlers import RotatingFileHandler

import sys
import json
import random
import logging
import argparse
import datetime

import constants
""" It is suggested to keep credentials.py is kept locally in the
    system where server is running. This file has been provided
    for reference.
"""

username_table = {u.username: u for u in credentials.users}
userid_table = {u.id: u for u in credentials.users}


def authenticate(username, password):
    user = username_table.get(username, None)
    if user and safe_str_cmp(
            user.password.encode('utf-8'),
            password.encode('utf-8')):
        return user


def identity(payload):
    user_id = payload['identity']
    return userid_table.get(user_id, None)


def setup_logging(app):
    # maxBytes and backupCount values to allow the file to rollover at a predetermined size.
    # When the size is about to be exceeded, the file is closed and a new file is silently
    # opened for output. Rollover occurs whenever the current log file is nearly maxBytes in length.
    # When backupCount is non-zero, the system will save old log files by appending the extensions
    # ‘.1’, ‘.2’ etc., to the filename.
    file_handler = RotatingFileHandler(
        "./flask.log",
        maxBytes=1024 * 1024 * 1024 * 5,
        backupCount=5)
    file_handler.setFormatter(
        logging.Formatter(
            '[%(asctime)s][PID:%(process)d][%(levelname)s]'
            '[%(lineno)s][%(name)s.%(funcName)s()] %(message)s'))
    file_handler.setLevel(logging.INFO)
    loggers = [app.logger]
    for logger in loggers:
        logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)


app = Flask(__name__)

setup_logging(app)

logger = logging.getLogger(__name__)

app.debug = True
app.config['SECRET_KEY'] = credentials.SECRET_KEY
app.config['JWT_EXPIRATION_DELTA'] = datetime.timedelta(
    days=constants.JWT_EXPIRATION_DAYS)

dbm = dbManager(app=app).start_daemon()

jwt = JWT(app, authenticate, identity)

# ----------------------- Database Methods ----------------------------------#


def store_to_db(data_dict):
    """
        Use the database manager to asynchronously update the database

        :param: data_dict: Dictionary containing data to be stored
    """
    validation, err_code = dbm.store(data_dict)
    return validation, err_code

# ----------------------- FLASK API Methods ---------------------------------- #


@app.route('/', methods=['POST'])
@jwt_required()
def add_db_entry():
    """
        Store received data to database if validation is okay

        :return: validation information and error code
    """

    data = request.get_json()
    app.logger.debug("Received Data (POST)")
    app.logger.debug(pformat(data))
    # Make sure the data is valid
    validation, err_code = DataValidator.validate_request_sanity(data)
    if validation == "OK":
        app.logger.info("<<<<VALIDATION OK>>>>")
        validation, err_code = store_to_db(data)
    else:
        app.logger.error("<<<<VALIDATION NOT OK>>>>")
        app.logger.error(pformat({"data": validation, "error_code": err_code}))
    info_json = jsonify({"data": validation, "error_code": err_code})
    return info_json, err_code


@app.route("/")
def home():
    info_json = jsonify({"type": "INFO", "data": "Quality Metrics"})
    return info_json, 200


if __name__ == '__main__':
    try:
        app.run(host=constants.LISTEN_ALL_IPS, port=5000)
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        app.logger.error("message")
        dbm.stop()
