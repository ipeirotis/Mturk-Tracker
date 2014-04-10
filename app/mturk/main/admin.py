# -*- coding: utf-8 -*-

import datetime
import logging

from django.views.generic.simple import direct_to_template
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.template import RequestContext
from django.contrib import auth
from django.conf import settings

from pythonsolr import  pysolr

from utils.sql import query_to_tuples
from mturk.main.templatetags.graph import text_row_formater
from models import RequesterProfile, HitGroupContent, IndexQueue
from html import strip_tags


log = logging.getLogger('mturk.main.admin')


def _hitgroup_content_to_sorl_dt(hg):
    """Convert given HitGroupContent object into valid solr dictionary, that
    can be added to index using at least pysolr.Solr connection
    """
    doc = {
        'group_id': hg.group_id,
        'requester_id': hg.requester_id,
        'requester_name': hg.requester_name,
        'reward': hg.reward,
        'content': strip_tags(hg.html),
        'description': strip_tags(hg.description),
        'title': hg.title,
        'keywords': [k.strip() for k in hg.keywords.split(',')],
        'qualifications': hg.qualifications,
        'occurrence_date': hg.occurrence_date,
        'time_alloted': hg.time_alloted,
    }
    return doc


def no_cache(view):
    """Decorator that disables any cache for view

    Instead of setting headers and other boring stuff, use django decorator
    with 0 cache timeout
    """
    wrapper = cache_page(0)
    return wrapper(view)


@login_required
@no_cache
def top_requesters(request):

    def row_formatter(input):
        "Yield formatted rows"
        for cc in input:
            row = []
            url = reverse('requester_details', kwargs={'requester_id': cc[0]})
            row.append('<a href="%s">%s</a>' % (url, cc[1]))
            row.append('<a href="{0}/mturk/searchbar?requesterId={1}" target="_mturk">{1}</a> (<a href="http://feed.crowdsauced.com/r/req/{1}">RSS</a>)'.format(
                settings.MTURK_PAGE, cc[0]
            ))
            row.extend(cc[2:6])
            url = reverse('admin-toggle-requester-status', args=(cc[0], ))
            row.append('<a href="%s">%s</a>' % (url, cc[6] and 'public' or 'private'))
            yield row

    date_30_days_before = datetime.date.today() - datetime.timedelta(days=30)
    data = row_formatter(query_to_tuples('''
            SELECT
                h.requester_id,
                h.requester_name,
                count(*) as "projects",
                sum(h.hits_available) as "hits",
                sum(h.hits_available*reward) as "reward",
                max(h.occurrence_date) as "last_posted",
                coalesce(p.is_public, true) as is_public
            FROM
                main_hitgroupfirstoccurences h
                    LEFT JOIN main_requesterprofile p ON h.requester_id = p.requester_id
            WHERE
                h.occurrence_date > %s
            GROUP BY
                h.requester_id, h.requester_name, p.is_public
            ORDER BY
                sum(h.hits_available*reward)
                DESC
            LIMIT 1000;
            ''', date_30_days_before))

    columns = (
        ('string', 'Requester ID'),
        ('string', 'Requester'),
        ('number', '#Task'),
        ('number', '#HITs'),
        ('number', 'Rewards'),
        ('datetime', 'Last Posted On'),
        ('string', 'Status'),
    )
    ctx = {
        'data': data,
        'columns': columns,
        'title': 'Top-1000 Recent Requesters',
    }
    return direct_to_template(request, 'main/graphs/table.html', ctx)


@login_required
@no_cache
def toggle_requester_status(request, id):
    """Toggle given requester private/public status"""
    rp, created = RequesterProfile.objects.get_or_create(requester_id=id)
    rp.is_public = not rp.is_public

    solr = pysolr.Solr(settings.SOLR_MAIN)
    if rp.is_public:
        # add hitgroups to solr index
        IndexQueue.objects.add_requester(rp.requester_id)

        # indexing large amount of data during single request might not be the
        # best idea...
        #hitgroups = HitGroupContent.objects.filter(requester_id=rp.requester_id)
        #log.debug('adding HitGroupContent objects to solr index: %s',
        #        [hg.group_id for hg in hitgroups])
        #solr.add([_hitgroup_content_to_sorl_dt(hg) for hg in hitgroups])
    else:
        # remove hitgroups from solr index
        solr.delete(q='requester_id:"%s"' % rp.requester_id)
        IndexQueue.objects.del_requester(rp.requester_id)
        log.debug('deleting HitGroupContent objects from solr index: %s',
                rp.requester_id)
    rp.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@no_cache
def requester_details(request, requester_id):
    def row_formatter(input):
        for cc in input:
            row = []
            url = reverse('hit_group_details', kwargs={'hit_group_id': cc[5]})
            row.append('<a href="%s">%s</a>' % (url, cc[0]))
            row.extend(cc[1:5])
            url = reverse('admin-toggle-hitgroup-status', args=(cc[5],))
            row.append('<a href="%s">%s</a>' % (url, cc[6] and 'public' or 'private'))
            yield row

    requester_name = HitGroupContent.objects.filter(requester_id=requester_id)
    requester_name = requester_name.values_list('requester_name', flat=True).distinct()

    if requester_name:
        requester_name = requester_name[0]
    else:
        requester_name = requester_id

    date_from = datetime.date.today() - datetime.timedelta(days=30)
    data = query_to_tuples("""
        SELECT
            title, hits_available, p.reward, p.occurrence_date,
            (SELECT end_time FROM main_crawl WHERE id = (SELECT max(crawl_id) FROM main_hitgroupstatus WHERE group_id = q.group_id AND hit_group_content_id = p.group_content_id)) - p.occurrence_date, p.group_id, q.is_public
        FROM
            main_hitgroupfirstoccurences p
                JOIN main_hitgroupcontent q ON (p.group_content_id = q.id AND p.requester_id = q.requester_id)
        WHERE
            p.requester_id = %s
            AND p.occurrence_date > %s
            AND q.occurrence_date > %s
        """, requester_id, date_from, date_from)

    columns = (
        ('string', 'HIT Title'),
        ('number', '#HITs'),
        ('number', 'Reward'),
        ('datetime', 'Posted'),
        ('number', 'Duration (Days)'),
        ('string', 'Status'),
    )

    ctx = {
        'data': text_row_formater(row_formatter(data)),
        'columns': tuple(columns),
        'title': 'Last 100 Tasks posted by %s' % requester_name,
        'user': request.user,
    }
    return direct_to_template(request, 'main/requester_details.html', ctx)


@login_required
@no_cache
def toggle_hitgroup_status(request, id):
    """Toggle given hitgroup public/private status, where id is the amazon hash key)
    """
    hg = get_object_or_404(HitGroupContent, group_id=id)
    hg.is_public = not hg.is_public
    solr = pysolr.Solr(settings.SOLR_MAIN)
    if hg.is_public:
        # add object to solr index
        doc = _hitgroup_content_to_sorl_dt(hg)
        log.debug('adding HitGroupContent to solr index: %s', doc)
        solr.add([doc])
    else:
        # remove from solr
        log.debug('removing HitGroupContent from solr index: %s', hg.group_id)
        IndexQueue.objects.del_hitgroupcontent(hg.group_id)
        solr.delete(q='group_id:"%s"' % hg.group_id)
    hg.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def logout(request):
    auth.logout(request)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def main_page(request):
    ctx = RequestContext(request)
    return render_to_response('admin/main.html', ctx)
