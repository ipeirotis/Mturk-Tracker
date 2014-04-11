# -*- coding: utf-8 -*-

import logging

from gevent import monkey
monkey.patch_all()
from gevent import socket

import psycopg2
from psycopg2 import extensions

from django.conf import settings


log = logging.getLogger(__name__)


def wait_callback(conn, timeout=None):
    while True:
        state = conn.poll()
        if state == extensions.POLL_OK:
            return
        elif state == extensions.POLL_READ:
            socket.wait_read(conn.fileno(), timeout=timeout)
        elif state == extensions.POLL_WRITE:
            socket.wait_write(conn.fileno(), timeout=timeout)
        else:
            log.error('Psycopg2 driver error. Bad result')
            raise psycopg2.OperationalError(
                "Bad result from poll: %r" % state)

# make postgresql driver work the async way
extensions.set_wait_callback(wait_callback)


class DB(object):
    """Simple proxy for psycopg2 connection object that allow to easily insert
    data into crawler tables.

    Be aware, that this object does not manage connection itself - you have to
    commit and close it by yourself.
    """
    def __init__(self, conn):
        self.conn = conn
        self.curr = self.conn.cursor()

    def hit_group_content_id(self, group_id):
        """Return hitgroup content object id related to given group or None if
        does not exists
        """
        self.curr.execute('''
            SELECT id FROM main_hitgroupcontent WHERE group_id = %s LIMIT 1
        ''', (group_id, ))
        # if len > 0, the group already exists in database
        result = self.curr.fetchone()
        if result is None:
            return result
        return result[0]

    def insert_hit_group_content(self, data):
        """Insert row into main_hitgroupcontent table and return it's id

        main_hitgroupcontent table contains UNIQUE contstaint on group_id
        column and because of that, inserting data with group_id that already
        exists it that table causes IntegrityError. When that happens, instead
        of throwing an exception, return id of already existing row.
        """
        try:
            self.curr.execute('''
                INSERT INTO main_hitgroupcontent(
                    reward, description, title, requester_name, qualifications,
                    time_alloted, html, keywords, requester_id, group_id,
                    group_id_hashed, occurrence_date, first_crawl_id, is_public,
                    last_updated, hits_available
                )
                VALUES (
                    %(reward)s, %(description)s, %(title)s, %(requester_name)s,
                    %(qualifications)s, %(time_alloted)s, %(html)s, %(keywords)s,
                    %(requester_id)s, %(group_id)s, %(group_id_hashed)s,
                    %(occurrence_date)s, %(first_crawl_id)s, %(is_public)s,
                    %(occurrence_date)s, 0
                )''', data)
            self.curr.execute("SELECT currval('main_hitgroupcontent_id_seq')")
        except psycopg2.IntegrityError:
            # this exception was caused because  hitgroupcontent with given
            # group_id already exists. Because of that, we do not have to
            # insert given data - just return id of already existing data row
            log.exception("""HitGroupConent insert IntegrityError, returning id:'
                %(reward)s, %(title)s, %(requester_name)s, %(qualifications)s,
                %(time_alloted)s, %(keywords)s, %(requester_id)s, %(group_id)s,
                 %(group_id_hashed)s, %(occurrence_date)s, %(first_crawl_id)s
                 """, data)
            self.conn.rollback()
            self.curr.execute('''
                SELECT id FROM main_hitgroupcontent WHERE group_id = %s LIMIT 1
            ''', (data['group_id'], ))
        return self.curr.fetchone()[0]

    def insert_hit_group_status(self, data):
        """Insert row into main_hitgroupstatus row"""
        self.curr.execute('''
            INSERT INTO main_hitgroupstatus (
                crawl_id, inpage_position, hit_group_content_id, page_number,
                group_id, hits_available, hit_expiration_date
            )
            VALUES (
                %(crawl_id)s, %(inpage_position)s, %(hit_group_content_id)s,
                %(page_number)s, %(group_id)s, %(hits_available)s,
                %(hit_expiration_date)s
            )''', data)

        self.curr.execute('''
            UPDATE main_hitgroupcontent
            SET hits_available = %(hits_available)s,
                last_updated = %(now)s
            WHERE id = %(hit_group_content_id)s
        ''', data)

        # add related hitgroupcontent id to index queue
        self.curr.execute('''
            INSERT INTO main_indexqueue (
                hitgroupcontent_id, requester_id, created
            )
            VALUES (
                %(hit_group_content_id)s, %(requester_id)s, now()
            )''', data)
