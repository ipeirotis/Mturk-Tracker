"This is a proposed stable environment settings file."
# Import common settings. DO NOT REMOVE.
from defaults import *

# Set up logging
import logging
from os.path import join as pjoin

LOG_DIRECTORY = "%(log_dir)s"
logging.basicConfig(
    level=logging.DEBUG,
    filename=pjoin(LOG_DIRECTORY, 'crawl.log'),
    filemode='a'
)

log = logging.getLogger(__name__)


DATABASES.update({
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '%(db_name)s',
        'USER': '%(db_user)s',
        'PASSWORD': '%(db_password)s',
        'HOST': 'localhost',
        'PORT': '%(db_port)s',
    },
})


DEBUG = False
TEMPLATE_DEBUG = False

KEEP_LOGGED_DURATION = 31 * 24 * 60 * 60

################## NO SETTINGS UNDER THIS LINE |#################
# Import local (custom for dev machine) settings file if exists.
# Instead of importing this module in try/except block, import this file only
# if exists. This will allow us to make sure, that code in local.py is correct
# and loads properly
local_settings = os.path.join(os.path.dirname(__file__), 'local.py')
if os.path.isfile(local_settings):
    from locals import *
################## NO SETTINGS UNDER THIS LINE |#################