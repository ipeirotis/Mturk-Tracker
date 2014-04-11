# -*- coding: utf-8 -*-

import datetime
from django.db import models, connection, transaction

from mturk.fields import JSONField


class Crawl(models.Model):
    """Represents one crawl.
    Crawls are frequent events, ran every 6 minutes.
    During a crawl, mturk hitgroups data is saved into:

    * HitGroupContent -- description of the task
    * HitGroupStatus -- task progress, eg. currently available hits

    """
    start_time = models.DateTimeField('Start Time')
    end_time = models.DateTimeField('End Time')
    hits_available = models.IntegerField('Hits avaliable', null=True,
        help_text="Number of hits available")
    hits_downloaded = models.IntegerField('Hits downloaded', null=True,
        help_text="Number of hits downloaded")
    groups_available = models.IntegerField('Groups available', null=True,
        help_text="Number of groups available")
    groups_downloaded = models.IntegerField('Groups downloaded', null=True,
        help_text="Number of groups dowloaded")
    success = models.BooleanField('Success',
        help_text="If the crawl was successful")
    errors = JSONField('Errors', blank=True, null=True,
        help_text="Error data in JSON format")
    old_id = models.IntegerField(null=True, blank=True, unique=True,
        db_index=True, help_text="Old id of the crawl if it was imported")
    has_diffs = models.BooleanField("Has Diffs", db_index=True, default=False,
        help_text="If hits differences were calculated for this crawl")
    is_spam_computed = models.BooleanField("Is spam computed", db_index=True,
        default=False, help_text="If this crawl was checked for spam")
    has_hits_mv = models.BooleanField("Has hits mv", db_index=True,
        default=False, help_text="If corresponding hits_mv entry exists")

    def start_day(self):
        return datetime.date(year=self.start_time.year,
                             month=self.start_time.month,
                             day=self.start_time.day)

    def __str__(self):
        return 'Crawl: ' + str(self.start_time) + ' ' + str(self.end_time)


class HitGroupContent(models.Model):
    """Description of a hitgroup with a given id. Only one entry per a hit
    group.

    """
    group_id = models.CharField('Group ID', max_length=50, db_index=True,
        unique=True)
    group_id_hashed = models.BooleanField(default=False,
        help_text="Group id hash")
    requester_id = models.CharField('Requester ID', max_length=50,
        db_index=True)
    requester_name = models.CharField('Requester name', max_length=10000)
    reward = models.FloatField('Reward')
    html = models.TextField('HTML', max_length=100000000)
    description = models.TextField('Description', max_length=1000000)
    title = models.CharField('Title', max_length=10000)
    keywords = models.CharField('Keywords', blank=True, max_length=10000,
        null=True)
    qualifications = models.CharField('Qualifications', blank=True,
        max_length=10000, null=True)
    occurrence_date = models.DateTimeField('First occurrence date', blank=True,
        null=True, db_index=True)

    hits_available = models.IntegerField('Last HITs available number', default=0)
    last_updated = models.DateTimeField(null=True, blank=True)

    '''
    Time in minutes
    '''
    time_alloted = models.IntegerField('Time alloted')
    first_crawl = models.ForeignKey(Crawl, blank=True, null=True,
        verbose_name="First crawl",
        help_text="The first crawl containing this group")
    is_public = models.BooleanField("Is public", default=True)
    is_spam = models.NullBooleanField("Is spam", db_index=True)

    @models.permalink
    def get_absolute_url(self):
        """Returns url to HIT group details page."""
        return ('hit_group_details', (), {'hit_group_id': self.group_id})

    def prepare_for_prediction(self):

        # import csv
        # import StringIO
        import re

        num_of_qualifications = len(self.qualifications.split(',')) \
                if self.qualifications else 0
        sanitized_html = re.sub(r'\n', ' ', self.html)
        sanitized_html = re.sub(r'\r', '', sanitized_html)

        # out = StringIO.StringIO()

        # writer = csv.writer(out)
        # writer.writerow(  )

        # csvrow = out.getvalue()
        # out.close()

        return [self.reward, self.description, self.title, self.requester_name,
            self.qualifications, num_of_qualifications, self.time_alloted,
            sanitized_html, self.keywords,
            "true" if self.is_public else "false"]

        # return csvrow


class HitGroupStatus(models.Model):
    """Contains information on hit group progress.
    There can be many records per each hit group.
    """
    group_id = models.CharField('Group ID', max_length=50)
    hits_available = models.IntegerField('Hits avaliable',
        help_text="Available hits")
    page_number = models.IntegerField('Page number',
        help_text="Page on which the group was found")
    inpage_position = models.IntegerField('Inpage position',
        help_text="Inpage position on which the group was found")
    hit_expiration_date = models.DateTimeField('Hit expiration Date')
    hit_group_content = models.ForeignKey(HitGroupContent,
        help_text="Hit group content", verbose_name="Hitgroup content")
    crawl = models.ForeignKey(Crawl, verbose_name="Crawl")


class DayStats(models.Model):
    """Statistics for one whole day."""

    date = models.DateField('Date', db_index=True)

    arrivals = models.IntegerField('Arrivals hits', default=0)
    arrivals_value = models.FloatField('Arrivals hits value', default=0)
    processed = models.IntegerField('Processed hits', default=0)
    processed_value = models.FloatField('Processed hits value', default=0)


class CrawlAgregates(models.Model):
    """Crawl aggregation used for display."""

    reward = models.FloatField("Reward")
    hits = models.IntegerField("Hits")
    projects = models.IntegerField("Projects")
    start_time = models.DateTimeField("Start time", db_index=True)
    spam_projects = models.IntegerField("Spam projects")
    crawl = models.ForeignKey(Crawl, verbose_name="Crawl")

    hits_posted = models.IntegerField("Hits posted", null=True, default=0)
    hits_consumed = models.IntegerField("Hits consumed", null=True, default=0)
    hitgroups_posted = models.IntegerField("Hitgroups posted", null=True)
    hitgroups_consumed = models.IntegerField("Hitgroups consumed", null=True)
    rewards_posted = models.FloatField("Rewards posted", null=True)
    rewards_consumed = models.FloatField("Rewards consumed", null=True)


class HitGroupFirstOccurences(models.Model):
    """Created when a hit group is first seen."""

    requester_id = models.CharField("Requester ID", max_length=50,
        db_index=True)
    group_id = models.CharField("Group ID", max_length=50, db_index=True)
    requester_name = models.CharField("Requester name", max_length=500)
    hits_available = models.IntegerField("Hits available")
    occurrence_date = models.DateTimeField("Occurrence date", db_index=True)
    reward = models.FloatField("Reward")

    crawl = models.ForeignKey(Crawl, verbose_name="Crawl")
    group_status = models.ForeignKey(HitGroupStatus,
        verbose_name="Group status")
    group_content = models.ForeignKey(HitGroupContent,
        verbose_name="Group content")


class RequesterProfileManager(models.Manager):
    def all_as_dict(self):
        """Return all related objects as dictionary, where keys are
        `requester_id` values. Cached.
        """
        # TODO - memcache?
        data = tuple((p.requester_id, p) for p in self.all())
        # dicts are mutable, so cache tuple and generate fresh dict with every
        # call
        return dict(data)


class RequesterProfile(models.Model):

    requester_id = models.CharField("Requester id", max_length=64,
        primary_key=True)
    is_public = models.BooleanField("Is public", default=True)

    objects = RequesterProfileManager()


class IndexQueueManager(models.Manager):
    def add_requester(self, requester_id):
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO main_indexqueue (
                hitgroupcontent_id, requester_id, created
            )
            SELECT
                id, requester_id, now()
            FROM
                main_hitgroupcontent
            WHERE
                requester_id = %s
        ''', (requester_id, ))
        transaction.commit_unless_managed()

    def del_requester(self, requester_id):
        self.filter(requester_id=requester_id).delete()

    def del_hitgroupcontent(self, hitgroupcontent_id):
        self.filter(group_id=hitgroupcontent_id).delete()


class IndexQueue(models.Model):
    """List of ids that should be indexed in sold.

    Because we don't have to be 100% sure that given hitgroupcontent_id exists
    in HitGroupContent table, instead of using ForeignKey, simple Integer was
    used.
    """
    hitgroupcontent_id = models.IntegerField()
    requester_id = models.CharField(max_length=64)
    created = models.DateTimeField(auto_now_add=True)

    objects = IndexQueueManager()


class HitGroupClass(models.Model):
    """ Contains information about classification.
    """
    group_id = models.CharField(max_length=50, db_index=True, unique=True)
    classes = models.IntegerField(db_index=True)
    probabilities = models.CharField(max_length=1000)


class HitGroupClassAggregate(models.Model):
    """ Contains classification aggregates.
    """
    crawl_id = models.IntegerField()
    start_time = models.DateTimeField()
    classes = models.IntegerField()
    hits_available = models.IntegerField()
