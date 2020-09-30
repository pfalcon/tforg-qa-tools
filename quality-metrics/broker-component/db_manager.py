#!/usr/bin/env python3

from __future__ import print_function

__copyright__ = """
/*
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
 """

""" db_manager.py:

    Database interface abstraction class. This class is aimed at providing an
    asynchronous interface between a blocking IO resource(database) and a
    public interface designed for high concurrency.

"""

import time
import threading
from queue import Queue
from pprint import pformat
from influxdb import InfluxDBClient

import constants
from data_converter import DataConverter


class dbManager(object):
    def __init__(self,
                 host=constants.HOST,
                 port=constants.PORT,
                 user=None,
                 password=None,
                 buff_size=constants.BUFF_SIZE,
                 poll_delay=constants.POLL_DELAY,
                 app=None):
        self.queue_buff_sz = buff_size
        self.poll_delay = poll_delay

        self.db_host = host
        self.db_port = port
        self.db_user = user
        self.db_pass = password
        self.write_queue = Queue(maxsize=self.queue_buff_sz)
        self.stop_threads = False
        self.app = app

        for key in constants.DATABASE_DICT:
            client = InfluxDBClient(host=self.db_host,
                                    port=self.db_port,
                                    username=self.db_user,
                                    password=self.db_pass,
                                    database=constants.DATABASE_DICT[key])
            setattr(self, key.lower() + '_client', client)

    def store(self, data):
        """
            Places data in the FIFO to be broadcast when
            the database is not busy

            :param: data: Data to be placed in FIFO
        """
        validation = 'OK'
        err_code = 204
        try:
            self.write_queue.put(data)
        except Exception as e:
            validation = "** Write to Queue Failed. ** "
            err_code = 402
            print(validation, e)
            self.app.logger.error(pformat({"error_code": err_code,
                                           "info": validation, "exception": e}))
        return validation, err_code

    def get_db_client(self, metrics):
        if "stats" in metrics:
            client = metrics.replace("_stats", "") + "_client"
        elif "tracking" in metrics:
            client = metrics.replace("_tracking", "") + "_client"
        else:
            client = metrics + "_client"
        if hasattr(self, client):
            return getattr(self, client)
        else:
            self.app.logger.error("Invalid metrics %" % (metrics))

    def write_db_direct(self, data):
        """
            Write data to database ( will block if database is busy )

            :param: data: data to be written to database
        """
        db_client = self.get_db_client(data['metadata']['metrics'])

        converted_data = DataConverter.convert_data(data)

        if db_client:
            if db_client.write_points(converted_data):
                self.app.logger.info(
                    "Writing to InfluxDB hosted at %s "
                    "has been successful for %s!" %
                    (self.db_host, data['metadata']['metrics']))
            else:
                self.app.logger.error(
                    "Writing to InfluxDB hosted at %s "
                    "has FAILED for %s!" %
                    (self.db_host, data['metadata']['metrics']))
        else:
            self.app.logger.error(
                "%s database not connected.." %
                data['metadata']['metrics'])

    def start_daemon(self):
        """
            Spawn a new thread that will consume data in the write FIFO
            and place it into the databse
        """

        def write_db_loop():

            while True:
                try:
                    time.sleep(self.poll_delay)
                    if self.stop_threads:
                        self.app.logger.info(
                            "\n ** Shutting Down Database Writer **")
                        return
                    elif self.write_queue.qsize() > 0:
                        dt = self.write_queue.get()
                        # Write the data to the databse
                        self.write_db_direct(dt)
                        self.write_queue.task_done()
                except Exception as e:
                    self.app.logger.error(
                        "** DB Writer Thread Failed. ** \n%s" % e)

        self.db_write_thread = threading.Thread(target=write_db_loop)
        self.db_write_thread.daemon = True
        self.db_write_thread.start()
        return self

    def stop(self):
        """
        Flag which terminates db_write_threads loop
        """
        self.app.logger.info("** Setting stop_threads to True  **")
        self.stop_threads = True
