"This is a proposed stable environment settings file."
# Import common settings. DO NOT REMOVE.
from defaults import *

# Set up logging
import logging
from os.path import join as pjoin

LOG_DIRECTORY = "%(log_dir)s"

# Overriding default logger settings
LOGGING['handlers']['crawl_log']['filename'] = pjoin(LOG_DIRECTORY, 'crawl.log')
LOGGING['handlers']['log_file']['filename'] = pjoin(LOG_DIRECTORY, 'main.log')
LOGGING['handlers']['solr_log']['filename'] = pjoin(LOG_DIRECTORY, 'solr.log')
LOGGING['handlers']['arrivals_log']['filename'] = pjoin(LOG_DIRECTORY, 'arrivals.log')
LOGGING['handlers']['aggregates_log']['filename'] = pjoin(LOG_DIRECTORY, 'aggregates.log')
LOGGING['handlers']['classification_log']['filename'] = pjoin(LOG_DIRECTORY, 'classification.log')
LOGGING['handlers']['toprequesters_log']['filename'] = pjoin(LOG_DIRECTORY, 'toprequesters.log')

RAVEN_CONFIG = RAVEN_CONFIG or {}
RAVEN_CONFIG['dsn'] = "%(sentry_dsn)s"

log = logging.getLogger(__name__)

# sudo -u postgres psql
# CREATE USER %(db_user)s WITH CREATEDB NOCREATEUSER ENCRYPTED PASSWORD
# E'%(db_password)s';
# CREATE DATABASE %(db_name)s' WITH OWNER %(db_user)s;
DATABASES.update({
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '%(db_name)s',
        'USER': '%(db_user)s',
        'PASSWORD': '%(db_password)s',
        'HOST': '%(db_host)s',
        'PORT': '%(db_port)s',
    },
})

RUN_DATA_PATH = "%(service_dir)s"

KEEP_LOGGED_DURATION = 31 * 24 * 60 * 60

CLASSIFIER_PATH = "%(project_dir)s/misc/classifier.json"

################## NO SETTINGS UNDER THIS LINE |#################
# Import local (custom for dev machine) settings file if exists.
# Instead of importing this module in try/except block, import this file only
# if exists. This will allow us to make sure, that code in local.py is correct
# and loads properly
local_settings = os.path.join(os.path.dirname(__file__), 'local.py')
if os.path.isfile(local_settings):
    from local import *
################## NO SETTINGS UNDER THIS LINE |#################
