#!/usr/bin/env python3

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" credentials.py:

    Credentials class. This is for reference only.

"""

# SECRET_KEY is set for reference purpose only
# It is recommended to change its value before deployment
SECRET_KEY = 'SECRET_KEY'


class User(object):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def __str__(self):
        return "User(id='%s')" % self.id


# User credentials are set for reference purpose only
# It is recommended to change these value accordingly before deployment
users = [
    User(1, 'metrics_1', 'metrics_pass_1'),
    User(2, 'metrics_2', 'metrics_pass_2'),
    User(3, 'tfa_metrics', 'tfa_metrics_pass'),
]
