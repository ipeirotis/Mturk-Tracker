# -*- coding: utf-8 -*-

import re
import datetime
import logging

log = logging.getLogger(__name__)


_RX_WHITECHARS_DUPLICATE = re.compile(r'\s{2,}')

_RX_HITS_MAINPAGE = \
    re.compile(r'''
        (\d+,?\d*)
        \s*?
        HITs
        </\w+?>
        \s*?
        available
    ''', re.M | re.X)

_RX_HITS_TOTALGROUPS = \
    re.compile(r'''
        of
        \s+
        (?P<total_grouphits>\d+)
        \s+
        Results
    ''', re.M | re.X)

_RX_HITS_LIST = \
    re.compile(r'''
        <a\s+class="capsulelink"[^>]*>\s*(?P<title>.*?)\s*</a>
        .*?

        # the following are optional, because it's not always available
        (:?
            hitId=(?P<hit_id>.*?)(&|")
            .*?
        )?
        (:?
            groupId=(?P<group_id>.*?)(&|")
            .*?
        )?


        Requester
        .*?
        <td[^>]*>
            \s*?
                <a[^>]*requesterId=(?P<requester_id>.*?)(&|")[^>]*>
                    (?P<requester_name>.*?)
                </a>
            \s*?
        </td>

        .*?
        HIT\s+Expiration\s+Date
        .*?
        <td[^>]*>
            (?P<hit_expiration_date>[^&]*)
        &

        .*?
        Time\s+Allotted
        .*?
        <td[^>]*>
            (?P<time_alloted>.*?)
        </td>

        .*?
        Reward
        .{,200}?
        <td[^>]*>
            #
            # <span> tag is optional, because this is something that has
            # changed recently and I'm not sure that this is now valid for all
            # listings..
            #
            (?:<span[^>]*>)?
                \$
                (?P<reward>[\.\d]*?)
            (?:</span>)?
        </td>

        .*?
        HITs\s+Available
        .*?
        <td[^>]*>
            (?P<hits_available>\d+)
        </td>

        .*?
        Description:
        .*?
        <td[^>]*>
            (?P<description>.*?)
        </td>

        .*?
        Keywords
        .*?
        <td[^>]*>
            \s*
            (?P<keywords>.*?)
            \s*
        </td>

        .*?
        Qualifications\s+Required
        .*?
        <tr[^>]*>
            (?P<qualifications>.*?)
        </table>
    ''', re.M | re.X | re.S)

_RX_HITS_LIST_KEYWORDS = \
    re.compile(r'''
        \s*
        <a[^>]*>
            (.+?)
        </a>
        \s*
    ''', re.M | re.X | re.S)

_RX_HITS_LIST_QUALIFICATIONS = \
    re.compile(r'''
        <td[^>]*>
            \s*
                (.+?)
            \s*
        </td>
    ''', re.M | re.X | re.S)

_RX_HITS_DETAILS = \
    re.compile(r'''
        \s+Duration
        .*?
        <td[^>]*>
        \s*
            (?P<duration>.*?)
        \s*
        </td>

        .*?

        # get the iframe source url
        (?:
            <iframe.*?src="
                (?P<iframe_src>[^"]+)
            "[^>]*></iframe>
        |
            <form.*?accept">
                (?P<html>.*?)
            </div>
            \s*?
            </form>
        )
    ''', re.M | re.X | re.S)


def human_timedelta_seconds(hd):
    """Convert any human timedelta value to minutes. Human time delta values
    are for example:
        * 1 hour
        * 30 minutes 3 weeks
        * 2 hours 1 minute 18 seconds
    """
    def _to_seconds(value, time_type):
        value = int(value)
        if time_type.startswith('week'):
            return value * 7 * 24 * 60
        if time_type.startswith('day'):
            return value * 24 * 60
        if time_type.startswith('hour'):
            return value * 60
        if time_type.startswith('minute'):
            return value
        if time_type.startswith('second'):
            return int(value / 60.0)
        log.error('Unknown timer type: %s', time_type)
        raise TypeError('Unknown time type: %s' % time_type)

    total = 0
    for delta in re.findall(r'(\d+)\s+(\S+)', hd):
        total += _to_seconds(*delta)
    return total


def rm_dup_whitechas(s, replacer=' '):
    """Replace every two or more whitechars with single space"""
    return _RX_WHITECHARS_DUPLICATE.sub(replacer, s)


def hits_mainpage(html):
    """Return number of available hits fetched from given html (should be
    fetched from https://www.mturk.com/mturk/welcome)

    Returns None if hits number was not found.
    """
    rx = _RX_HITS_MAINPAGE.search(html, 1)
    if rx is None:
        log.info('Hits number not found')
        return None
    matched = rx.groups()[0]
    return int(matched.replace(',', ''))


def hits_group_listinfo(html):
    """Yield info about every hits group found in given html string

    Page should be fetched from
    https://www.mturk.com/mturk/findhits?match=false
    """
    rx_i = _RX_HITS_LIST.finditer(html)
    for rx in rx_i:
        res = rx.groupdict()

        # make parse result more polite and convert to python objects
        res['reward'] = float(res['reward'])
        res['hit_expiration_date'] = datetime.datetime.strptime(
                res['hit_expiration_date'], '%b %d, %Y')
        res['hits_available'] = int(res['hits_available'])
        res['keywords'] = _RX_HITS_LIST_KEYWORDS.findall(res['keywords'])
        qualifications = _RX_HITS_LIST_QUALIFICATIONS.findall(
            res['qualifications'])
        res['qualifications'] = [rm_dup_whitechas(q) for q in qualifications]
        # group id is not always available but hit id in the 'why' link should
        # point to correct group id
        res['hit_id'] = res.get('hit_id', None)
        res['group_id'] = res.get('group_id', None)
        # convert time allotated to seconds
        res['time_alloted'] = human_timedelta_seconds(res['time_alloted'])

        yield res


def hits_group_details(html):
    """Get more details info about single group of hits"""
    rx = _RX_HITS_DETAILS.search(html)
    if not rx:
        return {}
    res = rx.groupdict()
    res['html'] = res.get('html', None)
    res['duration'] = human_timedelta_seconds(res['duration'])
    return res


def hits_group_total(html):
    """Return total number of available hits groups.

    This info is being fetched from first mturk search page (pagination info)
    """
    rx = _RX_HITS_TOTALGROUPS.search(html, 1)
    if not rx:
        log.info('total hits groups number not found')
        return None
    res = rx.groupdict()
    return int(res['total_grouphits'])


def is_limit_exceeded(html):
    """Searchs the html for limit exceeded message.
    Used to distinguish empty page from temporary wait.

    """
    return html.find("You have exceeded the maximum allowed page"
        " request rate for this website.") != -1
