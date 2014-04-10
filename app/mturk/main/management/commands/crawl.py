# -*- coding: utf-8 -*-

import sys

try:
    from gevent import monkey
    monkey.patch_all()
except ImportError:
    sys.exit('Gevent library is required: http://www.gevent.org/')


import os
import time
import datetime
import logging
from logging.config import fileConfig
from optparse import make_option
from psycopg2.pool import ThreadedConnectionPool

import gevent
from django.core.management.base import BaseCommand
from django.conf import settings

from utils.pid import Pid
from crawler import tasks
from crawler import auth
from mturk.main.models import Crawl, RequesterProfile


log = logging.getLogger(__name__)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
            make_option('--workers', dest='workers', type='int', default=3,
                help='Use given number of concurrent crawl workers'),
            make_option('--logconf', dest='logconf', metavar='FILE',
                help='Load logging configuration from given file'),
            make_option('--debug', dest='debug', action='store_true',
                help='Work in debug mode (on fly pdb support)'),
            make_option('--mturk-email', dest='mturk_email',
                help='Mturk authentication email'),
            make_option('--mturk-password', dest='mturk_password',
                help='Mturk authentication password'),
    )

    def setup_logging(self, conf_fname):
        "Basic setup for logging module"
        fileConfig(conf_fname)
        if not os.path.isfile(conf_fname):
            raise IOError('File not found: %s' % conf_fname)
        log.info('logging conf: %s', conf_fname)

    def setup_debug(self):
        from crawler.debug import debug_listen
        debug_listen()

    def _authenticate_if_possible(self, email=None, password=None):
        """If possible - authenticate.  Mturk requires authentication for
        listing pagination pages greater that 20

        Return ``True`` if authentication was done successfully, else
        ``False``.
        """
        if self.mturk_email and self.mturk_password:
            auth.install_opener()
            resp = auth.authenticate(
                email=email or self.mturk_email,
                password=password or self.mturk_password
            )
            if resp.getcode() != 200:
                raise Exception('Authentiaction error: %s' % resp.read())
            log.info('Mturk authentication done')
            return True
        log.warning('No mturk authentication')
        return False

    def handle(self, *args, **options):

        self.mturk_email = getattr(settings, 'MTURK_AUTH_EMAIL', None)
        self.mturk_password = getattr(settings, 'MTURK_AUTH_PASSWORD', None)

        _start_time = time.time()
        pid = Pid('mturk_crawler', True)
        log.info('crawler started: %s;;%s', args, options)

        if options.get('mturk_email'):
            self.mturk_email = options['mturk_email']
        if options.get('mturk_password'):
            self.mturk_password = options['mturk_password']

        if options.get('logconf', None):
            self.setup_logging(options['logconf'])

        if options.get('debug', False):
            self.setup_debug()
            print 'Current proccess pid: %s' % pid.actual_pid
            print ('To debug, type: python -c "import os,signal; '
                'os.kill(%s, signal.SIGUSR1)"\n') % pid.actual_pid

        self.maxworkers = options['workers']
        if self.maxworkers > 9:
            # If you want to remote this limit, don't forget to change dbpool
            # object maximum number of connections. Each worker should fetch
            # 10 hitgroups and spawn single task for every one of them, that
            # will get private connection instance. So for 9 workers it's
            # already 9x10 = 90 connections required
            #
            # Also, for too many workers, amazon isn't returning valid data
            # and retrying takes much longer than using smaller amount of
            # workers
            sys.exit('Too many workers (more than 9). Quit.')
        start_time = datetime.datetime.now()

        hits_available = tasks.hits_mainpage_total()
        groups_available = tasks.hits_groups_total()

        # create crawl object that will be filled with data later
        crawl = Crawl.objects.create(
                start_time=start_time,
                end_time=start_time,
                success=True,
                hits_available=hits_available,
                hits_downloaded=0,
                groups_available=groups_available,
                groups_downloaded=groups_available)
        log.debug('fresh crawl object created: %s', crawl.id)

        # fetch those requester profiles so we could decide if their hitgroups
        # are public or not
        reqesters = RequesterProfile.objects.all_as_dict()

        dbpool = ThreadedConnectionPool(10, 90,
            'dbname=%s user=%s password=%s' % (
                settings.DATABASES['default']['NAME'],
                settings.DATABASES['default']['USER'],
                settings.DATABASES['default']['PASSWORD']))
        # collection of group_ids that were already processed - this should
        # protect us from duplicating data
        processed_groups = set()
        total_reward = 0
        hitgroups_iter = self.hits_iter()

        for hg_pack in hitgroups_iter:
            jobs = []
            for hg in hg_pack:
                if hg['group_id'] in processed_groups:
                    log.debug('Group already in processed_groups, skipping.')
                    continue
                processed_groups.add(hg['group_id'])

                j = gevent.spawn(tasks.process_group,
                        hg, crawl.id, reqesters, processed_groups, dbpool)
                jobs.append(j)
                total_reward += hg['reward'] * hg['hits_available']
            log.debug('processing pack of hitgroups objects')
            gevent.joinall(
                jobs, timeout=settings.CRAWLER_GROUP_PROCESSING_TIMEOUT)
            # check if all jobs ended successfully
            for job in jobs:
                if not job.ready():
                    log.info('Killing job: %s', job)
                    job.kill()

            if len(processed_groups) >= groups_available:
                log.info('Skipping empty groups.')
                # there's no need to iterate over empty groups.. break
                break

            # amazon does not like too many requests at once, so give them a
            # quick rest...
            gevent.sleep(1)

        dbpool.closeall()

        # update crawler object
        crawl.groups_downloaded = len(processed_groups)
        crawl.end_time = datetime.datetime.now()
        crawl.save()

        work_time = time.time() - _start_time
        log.info("""Crawl finished:
        created crawl id: {crawl_id})
        total reward value: {total_reward}
        hits groups downloaded: {processed_groups}
        hits groups available: {groups_available}
        work time: {work_time:.2f} seconds
        """.format(crawl_id=crawl.id, total_reward=total_reward,
            processed_groups=len(processed_groups),
            groups_available=groups_available,
            work_time=work_time))

        crawl_downloaded_pc = settings.INCOMPLETE_CRAWL_THRESHOLD
        crawl_warning_pc = settings.INCOMPLETE_CRAWL_WARNING_THRESHOLD
        crawl_time_warning = settings.CRAWLER_TIME_WARNING
        downloaded_pc = float(crawl.groups_downloaded) / groups_available
        if work_time > crawl_time_warning:
            log.warning(("Crawl took {0}s which seems a bit too long (more "
                "than {1}s), you might consider checking if correct mturk "
                "account is used, ignore this if high number of groups is "
                "experienced.").format(work_time, crawl_time_warning))
        if downloaded_pc < crawl_warning_pc:
            log.warning(('Only {0}% of hit groups were downloaded, below '
                '({1}% warning threshold) please check mturk account '
                'configuration and/or if there are any network-related '
                'problems.').format(downloaded_pc, crawl_warning_pc))
        if downloaded_pc < crawl_downloaded_pc:
            log.warning("This crawl contains far too few groups downloaded to "
                "available: {0}% < {1}% downloaded threshold and will be "
                "considered as erroneous ({2}/{3} groups).".format(
                    downloaded_pc, crawl_downloaded_pc,
                    crawl.groups_downloaded, groups_available))

        pid.remove_pid()

    def hits_iter(self):
        """Hits group lists generator.

        As long as available, return lists of parsed hits group. Because this
        method is using concurent download, number of returned elements on
        each list cannot be greater that maximum number of workers.

        On start, the number of pages could be estimated using fetched
        groups_avaialable and the number of crawls per page. However the number
        will change during the crawl as tasks are posted and completed and can
        be only estimated with precision of roughly 1-3 page.

        Therefore finding an empty page is the stop condition.

        """
        self._authenticate_if_possible()

        counter = count(1, self.maxworkers)
        for i in counter:
            pages = range(i, i + self.maxworkers)
            log.debug('Processing pages: {0}'.format(pages))
            jobs = [gevent.spawn(tasks.hits_groups_info, page_nr)
                for page_nr in pages]
            gevent.joinall(jobs)

            # get data from completed tasks & remove empty results
            hgs = []
            for job in jobs:
                if job.value:
                    hgs.extend(job.value)

            # if no data was returned, end - previous page was probably the
            # last one with results
            if not hgs:
                log.info('None of the pages {0} contains data, assuming all '
                    'pages were processed, exiting.'.format(pages))
                break

            log.debug('yielding hits group: %s', len(hgs))
            yield hgs


def count(firstval=0, step=1):
    "Port of itertools.count from python2.7"
    while True:
        yield firstval
        firstval += step
