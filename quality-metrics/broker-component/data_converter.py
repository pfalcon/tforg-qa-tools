#!/usr/bin/env python3

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" data_converter.py:

    Data converter class. This class is aimed at converting the received
    data in the format which InfluxDB understands.

"""

import json
import constants


class DataConverter:

    @staticmethod
    def convert_tfm_imagesize_data(data):
        # Transform keys names
        data['metadata']['DataProducer'] = data['metadata'].pop(
            'data_producer')

        data['metadata']['git_info']['CommitTitle'] = data['metadata']['git_info'].pop(
            'commit_title')
        data['metadata']['git_info']['CommitID'] = data['metadata']['git_info'].pop(
            'commit_id')
        data['metadata']['git_info']['GerritID'] = data['metadata']['git_info'].pop(
            'gerrit_id')
        data['metadata']['git_info']['CommitURL'] = data['metadata']['git_info'].pop(
            'commit_url')
        data['metadata']['git_info']['Branch'] = data['metadata']['git_info'].pop(
            'branch')

        data['metadata']['build_info']['BuildType'] = data['metadata']['build_info'].pop(
            'build_type')
        data['metadata']['build_info']['CmakeConfig'] = data['metadata']['build_info'].pop(
            'cmake_config')
        data['metadata']['build_info']['Compiler'] = data['metadata']['build_info'].pop(
            'compiler')
        data['metadata']['build_info']['Target'] = data['metadata']['build_info'].pop(
            'target')

        ret = {}
        ret['tags'] = {}
        ret['fields'] = {}

        ret['measurement'] = 'TFM_ImageSize_Statistics'

        for file_info in data['data']:
            ret['fields'][file_info['file'].rsplit(
                '.', 1)[0] + '_b'] = file_info['bss']
            ret['fields'][file_info['file'].rsplit(
                '.', 1)[0] + '_d'] = file_info['data']
            ret['fields'][file_info['file'].rsplit(
                '.', 1)[0] + '_t'] = file_info['text']

        ret['tags']['DataProducer'] = str(data['metadata']['DataProducer'])

        ret['time'] = str(data['metadata']['git_info']['commit_time'])

        for key in data['metadata']['git_info']:
            if key == 'commit_time':
                continue
            ret['tags'][key] = str(data['metadata']['git_info'][key])

        for key in data['metadata']['build_info']:
            ret['tags'][key] = str(data['metadata']['build_info'][key])

        print(ret)

        return [ret]

    @staticmethod
    def convert_data(data):
        """
            Convert data to a dictionary containing measurement
            name, fields and tags. It is required by InfluxDB.

            :param data: data to be converted to InfluxDB format
        """

        if data['metadata']['metrics'] == 'tfm_imagesize':
            ret = DataConverter.convert_tfm_imagesize_data(data)
        else:
            ret = data['data']

        return ret
