# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'HitGroupContent.hits_available'
        db.add_column('main_hitgroupcontent', 'hits_available',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'HitGroupContent.last_updated'
        db.add_column('main_hitgroupcontent', 'last_updated',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'HitGroupContent.hits_available'
        db.delete_column('main_hitgroupcontent', 'hits_available')

        # Deleting field 'HitGroupContent.last_updated'
        db.delete_column('main_hitgroupcontent', 'last_updated')


    models = {
        'main.crawl': {
            'Meta': {'object_name': 'Crawl'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {}),
            'errors': ('mturk.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'groups_available': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'groups_downloaded': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'has_diffs': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'has_hits_mv': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'hits_available': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'hits_downloaded': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_spam_computed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'old_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'main.crawlagregates': {
            'Meta': {'object_name': 'CrawlAgregates'},
            'crawl': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Crawl']"}),
            'hitgroups_consumed': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'hitgroups_posted': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'hits': ('django.db.models.fields.IntegerField', [], {}),
            'hits_consumed': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'hits_posted': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projects': ('django.db.models.fields.IntegerField', [], {}),
            'reward': ('django.db.models.fields.FloatField', [], {}),
            'rewards_consumed': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'rewards_posted': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'spam_projects': ('django.db.models.fields.IntegerField', [], {}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        'main.daystats': {
            'Meta': {'object_name': 'DayStats'},
            'arrivals': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'arrivals_value': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'processed': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'processed_value': ('django.db.models.fields.FloatField', [], {'default': '0'})
        },
        'main.hitgroupclass': {
            'Meta': {'object_name': 'HitGroupClass'},
            'classes': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'group_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'probabilities': ('django.db.models.fields.CharField', [], {'max_length': '1000'})
        },
        'main.hitgroupclassaggregate': {
            'Meta': {'object_name': 'HitGroupClassAggregate'},
            'classes': ('django.db.models.fields.IntegerField', [], {}),
            'crawl_id': ('django.db.models.fields.IntegerField', [], {}),
            'hits_available': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {})
        },
        'main.hitgroupcontent': {
            'Meta': {'object_name': 'HitGroupContent'},
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000000'}),
            'first_crawl': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Crawl']", 'null': 'True', 'blank': 'True'}),
            'group_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'group_id_hashed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hits_available': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'html': ('django.db.models.fields.TextField', [], {'max_length': '100000000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_spam': ('django.db.models.fields.NullBooleanField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'keywords': ('django.db.models.fields.CharField', [], {'max_length': '10000', 'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'occurrence_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'qualifications': ('django.db.models.fields.CharField', [], {'max_length': '10000', 'null': 'True', 'blank': 'True'}),
            'requester_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'requester_name': ('django.db.models.fields.CharField', [], {'max_length': '10000'}),
            'reward': ('django.db.models.fields.FloatField', [], {}),
            'time_alloted': ('django.db.models.fields.IntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '10000'})
        },
        'main.hitgroupfirstoccurences': {
            'Meta': {'object_name': 'HitGroupFirstOccurences'},
            'crawl': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Crawl']"}),
            'group_content': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.HitGroupContent']"}),
            'group_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'group_status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.HitGroupStatus']"}),
            'hits_available': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'occurrence_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'requester_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'requester_name': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'reward': ('django.db.models.fields.FloatField', [], {})
        },
        'main.hitgroupstatus': {
            'Meta': {'object_name': 'HitGroupStatus'},
            'crawl': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Crawl']"}),
            'group_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'hit_expiration_date': ('django.db.models.fields.DateTimeField', [], {}),
            'hit_group_content': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.HitGroupContent']"}),
            'hits_available': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inpage_position': ('django.db.models.fields.IntegerField', [], {}),
            'page_number': ('django.db.models.fields.IntegerField', [], {})
        },
        'main.indexqueue': {
            'Meta': {'object_name': 'IndexQueue'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'hitgroupcontent_id': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'requester_id': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'main.requesterprofile': {
            'Meta': {'object_name': 'RequesterProfile'},
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'requester_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'primary_key': 'True'})
        }
    }

    complete_apps = ['main']