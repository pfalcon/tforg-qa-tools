#!/usr/bin/env python3

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" tfa_defects.py:

    Retrieves TF-A defects from GitHub

"""

from github import GitHub, ApiError, ApiNotFoundError

try:
    token = "<GitHub Access Token>"
    gh = GitHub(access_token=token)

    # Please note that currently 'open' defects are reported
    # In future, labels='bug' would be used for defect density
    open_bug_issues = gh.repos(
        'ARM-software')('tf-issues').issues.get(state='open', labels='bug')

    bugCounter = 0

    TFA_URL = "https://github.com/ARM-software/tf-issues/issues/"

    for issue in open_bug_issues:
        print("Found open bug with id: %s: %s, %s" %
              (issue.number, issue.title, issue.state))
        bugCounter += 1

        print("\t url for this issue is: %s" % (TFA_URL + str(issue.number)))

    print("@@ Total number of open bugs: %d" % (bugCounter))

except ApiNotFoundError as e:
    print(e, e.request, e.response)
