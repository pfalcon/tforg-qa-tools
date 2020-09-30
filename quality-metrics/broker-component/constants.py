#!/usr/bin/env python3

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" constants.py:

    This file contains the constants required by metrics server.

"""

JWT_EXPIRATION_DAYS = 365

HOST = "<Host Public IP Address>"
PORT = "8086"
BUFF_SIZE = 10
POLL_DELAY = 0.1

LISTEN_ALL_IPS = "0.0.0.0"

VALID_METRICS = [
    'tfm_image_size',
    'tfa_code_churn',
    'tfa_defects_stats',
    'tfa_defects_tracking',
    'tfa_complexity_stats',
    'tfa_complexity_tracking',
    'tfa_rtinstr',
    'tfa_image_size',
    'tfa_misra_defects']

DATABASE_DICT = {
    "TFM_IMAGE_SIZE": "TFM_ImageSize",
    "TFA_CODE_CHURN": "TFA_CodeChurn",
    "TFA_DEFECTS": "TFA_Defects",
    "TFA_COMPLEXITY": "TFA_Complexity",
    "TFA_RTINSTR": "TFA_RTINSTR",
    "TFA_IMAGE_SIZE": "TFA_ImageSize",
    "TFA_MISRA_DEFECTS": "TFA_MisraDefects"
}

SUPPORTED_API_VERSIONS = ["1.0"]
