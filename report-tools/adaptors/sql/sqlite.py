##############################################################################
# Copyright (c) 2021, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################
"""
SQL adaptor for SQLite queries
"""
import sqlite3


class Database:
    """
    Class used to represent an sqlite database

    Methods:
        execute_query: Executes and sqlite query and returns response
    """

    def __init__(self, db):
        """Inits Database class with an sqlite db instance"""
        self.mydb = sqlite3.connect(db)
        self.cursor = self.mydb.cursor()

    def execute_query(self, query):
        """Executes a sqlite query
        Args:
            query(str): sqlite query
        Returns:
            response to the query
        """
        try:
            self.cursor.execute(query)
            self.mydb.commit()
            return self.cursor.fetchall()
        except sqlite3.Error as err:
            raise err
