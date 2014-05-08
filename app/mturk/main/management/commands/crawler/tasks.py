# -*- coding: utf-8 -*-

import ssl
import logging
import urllib2
import datetime
import hashlib

import gevent
from gevent import thread

import parser
from db import DB
from django.conf import settings


log = logging.getLogger(__name__)


def _download_html(url, timeout=10):
    """Get page code using given url. If server won't response in `timeout`
    seconds, return empty string.
    """
    try:
        return urllib2.urlopen(url, timeout=timeout).read()
    except (urllib2.URLError, ssl.SSLError):
        pass
    # except (urllib2.URLError, ssl.SSLError), e:
    #     log.error('%s;;%s;;%s', type(e).__name__, url, e.args)
    return ''


def _get_html(url, timeout=settings.CRAWLER_FETCH_TIMEOUT,
        sleep=settings.CRAWLER_RETRY_SLEEP,
        retries=settings.CRAWLER_RETRY_COUNT):
    while retries > 0:
        html = _download_html(url, timeout=timeout)

        if html == '' or parser.is_limit_exceeded(html):
            rs = settings.CRAWLER_RETRY_COUNT - retries + 1

            if rs > settings.CRAWLER_RETRY_WARNING:
                level = logging.WARNING
            else:
                level = logging.DEBUG

            log.log(level, ('Limit exceeded, retrying download: {0}/{1} ({2}'
                ' sleep)\nurl: {3}').format(
                rs, settings.CRAWLER_RETRY_COUNT, sleep, url))
            gevent.sleep(sleep)
            retries -= 1
        else:
            return html
    else:
        log.warning('Downloader retry limit exceeded. Either the limit '
            'is too small, some unknown bug was encountered or there is a '
            'connection error.')


def hitsearch_url(page=1):
    return '{}/mturk/viewhits?searchWords=&selectedSearchType=hitgroups&sortType=LastUpdatedTime:1&pageNumber={}&searchSpec=HITGroupSearch%23T%231%2310%23-1%23T%23!%23!LastUpdatedTime!1!%23!'.format(
        settings.MTURK_PAGE, page
    )


def group_url(id):
    return "{}/mturk/preview?groupId={}".format(settings.MTURK_PAGE, id)


def amazon_review_url(id):
    return "http://www.amazon.com/review/%s" % id


def hits_mainpage_total():
    """Get total available hits from mturk main page"""
    url = '{}/mturk/welcome'.format(settings.MTURK_PAGE)
    html = _get_html(url)
    return parser.hits_mainpage(html)


def hits_groups_info(page_nr,
        retries=getattr(settings, 'CRAWLER_RETRY_COUNT', 200),
        sleep=getattr(settings, 'CRAWLER_RETRY_SLEEP', 0.1)):
    """Returns info about every hit group on the given page.

    Since mturk.com enforces a limit on the number of connections to the
    website, often the process must retry downloads. Retries will continue as
    long as the html downloaded is empty or includes limit exceeded message.

    Keyword arguments:
    page_nr -- page to process
    retries -- number of retries to make, by default a big number
    sleep -- how long to wait between each retry

    """
    def __fix_missing_hash(hg):
        hg['group_id_hashed'] = not bool(hg.get('group_id', None))
        if hg['group_id_hashed']:
            hg['group_id'] = hg.get('hit_id', None)
            log.debug('group id not found, trying hit_id %s', hg['group_id'])
            if not hg['group_id']:
                composition = ';'.join(map(str, (
                    hg['title'], hg['requester_id'], hg['time_alloted'],
                    hg['reward'], hg['description'], hg['keywords'],
                    hg['qualifications']))) + ';'
                hg['group_id'] = hashlib.md5(composition).hexdigest()
                log.debug('hit_id not found, creating hash: %s  %s',
                          hg['group_id'], hg['title'])
    url = hitsearch_url(page_nr)
    html = _get_html(url)
    rows = []
    for n, info in enumerate(parser.hits_group_listinfo(html)):
        __fix_missing_hash(info)
        info['page_number'] = page_nr
        info['inpage_position'] = n + 1
        rows.append(info)
    log.debug('hits_groups_info done: %s;;%s', page_nr, len(rows))

    if not rows:
        log.debug('No content in page {0}, returning'.format(page_nr))

    return rows


def hits_group_info(group_id):
    """Return info about given hits group"""
    url = group_url(group_id)
    html = _get_html(url)
    data = parser.hits_group_details(html)
    if not data:
        log.warning('Could not fetch hit group info: {0}'.format(group_id))
    # additional fetch of example task
    iframe_src = data.get('iframe_src', None)
    if iframe_src:
        log.debug('fetching iframe source: %s;;%s', url, iframe_src)
        data['html'] = _get_html(iframe_src, 4)
    elif data.get('html', None) is None:
        data['html'] = ''
    return data


def hits_groups_total():
    """Return total number of hits groups or None"""
    url = "{}/mturk/findhits?match=false".format(settings.MTURK_PAGE)
    html = _get_html(url)
    return parser.hits_group_total(html)


def process_group(hg, crawl_id, requesters, processed_groups, dbpool):
    """Gevent worker that should process single hitgroup.

    This should write some data into database and do not return any important
    data.
    """
    hg['keywords'] = ', '.join(hg['keywords'])
    # for those hit goups that does not contain hash group, create one and
    # setup apropiate flag

    hg['qualifications'] = ', '.join(hg['qualifications'])

    conn = dbpool.getconn(thread.get_ident())
    db = DB(conn)
    try:
        hit_group_content_id = db.hit_group_content_id(hg['group_id'])
        if hit_group_content_id is None:
            # check if there's profile for current requester and if does
            # exists with non-public status, then setup non public status for
            # current hitsgroup content
            profile = requesters.get(hg['requester_id'], None)
            if profile and profile.is_public is False:
                hg['is_public'] = False
            else:
                hg['is_public'] = True
            # fresh hitgroup - create group content entry, but first add some data
            # required by hitgroup content table
            hg['occurrence_date'] = datetime.datetime.now()
            hg['first_crawl_id'] = crawl_id
            if not hg['group_id_hashed']:
                # if group_id is hashed, we cannot fetch details because we
                # don't know what the real hash is
                hg.update(hits_group_info(hg['group_id']))
            else:
                hg['html'] = ''
            hit_group_content_id = db.insert_hit_group_content(hg)
            log.debug('new hit group content: %s;;%s',
                    hit_group_content_id, hg['group_id'])

        hg['hit_group_content_id'] = hit_group_content_id
        hg['crawl_id'] = crawl_id
        hg['now'] = datetime.datetime.now()
        db.insert_hit_group_status(hg)
        conn.commit()
    except Exception:
        processed_groups.remove(hg['group_id'])
        log.exception('process_group fail - rollback')
        conn.rollback()
    finally:
        db.curr.close()
        dbpool.putconn(conn, thread.get_ident())
        msg = ('This really should not happen, Hitgroupstatus was processed but'
            ' is not on the list, race condition?')
        assert hg['group_id'] in processed_groups, msg

    return True
