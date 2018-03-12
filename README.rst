This is depracated software. For the most recent version of the MTurk Tracker see https://github.com/ipeirotis/mturk-tracker-gae (note: that version also stopped working on February 29th, 2016)

Mturk-Tracker
=============

Mturk-Tracker is a Django web application and it is setup within python
virtualenv and requires a working python environment, PostgreSQL database and
Solr search engine.

Source / How to get it
======================

Visit github repository at

    https://github.com/ipeirotis/Mturk-Tracker/

What's new
==========

Search
Crawler improvements

What's included?
================

The application consists of two main components:

* the website (as seen at http://mturk-tracker.com/)
* web crawler (tracking http://www.mturk.com/)

Documentation
=============

This file is only an introduction to the project and is also avalable at:

    http://mturk-tracker.com/documentation/

whereas the complete project documentation can be found at:

    http://mturk-tracker.com/documentation/mturk-tracker/

The web api documentation is available at:

    http://mturk-tracker.com/documentation/mturk-tracker/api/

How does it work?
=================

Website
-------

As it mentioned before Mturk-Tracker site is written in Django Python web
framework.

Crawlers
--------

Amazon mturk site mturk.com is searched for available hit groups on a regular
basis (approx each 6 minutes). For each encountered hit group, it's current
status (number of hits available) and, if possible, if content are downloaded
and saved to the database.

The data is further processed, preparing it for display and search.

Automatic project setup
=======================

This option is the easiset mean of installing the application on a target
machine, however it will install all the components as there is currently no
mean of excluding certain modules.

Currently deployment scripts should cover everything you need to setup the
project. Only basic system configuration is required. First, create an user
account which will have ownership to the project files and run ssh-server
deamon.

Most things in the project are parametrized. The project configuration is based
on json files that contain these parameters. Code responsible for deployment
process exists in ``path/to/Mturk-Tracker/deployment/`` subdirectory. There is
a fabric script responsible for most of deployment logic and templates of
configuration files that are filled with deployment parameters.

Two major files that contains deployment parameters:

#. ``default.json`` - contains settings common across all project instances,
   such as the repository URL.
#. ``site-name.json`` - contains settings specific for certain project. It also
   contains sensitive data thus it does not exist in the repository.

Data from this files is used for generation of resultant configuration files
and scripts on the destination machine.

The structure of ``default.json`` file
--------------------------------------

This file exists in the repository. It contains parameters common for all
project instances. Only several parameters are usually overriden by
``site-name.json`` that is described in the next section.

The structure of ``site-name.json`` file
----------------------------------------

This file should contain instance-specyfic deployment parameters:

* ``projects_dir`` - path to the destination directory where the project files
  are to be stored;
* ``settings_name`` - name of the resultant settings file, that will be created
  from settings template.
* ``locals_path`` - path to the additional custom Django settings file that you
  want to upload on the destination machine;
* ``db_name`` - name of the database;
* ``db_user`` - name of the database user used by crawler;
* ``db_password`` - password for the crawler database user;
* ``solr_db_user`` - name of the database user used by Solr during data import;
* ``sorl_db_password`` - password for the Solr database user;
* ``pip_requirements`` - list files that contanins set of Python packages to be
  installed by pip;
* ``system_requirements`` - files that constains lists of system packages to be
  installed by system package manager;
* ``branch`` - name of the repository branch;
* ``pip_cache`` - path to the directory where pip packages are cached on the
  destination machine;

Example ``site-name.json`` file:

::

	{
		"projects_dir": "/data/projects",
		"settings_name": "site-name",
		"db_name": "db",
		"db_user": "db_user",
		"db_password": "****",
		"solr_db_user": "db_solr_user",
		"solr_db_password": "*****",
		"pip_requirements": ["base.txt", "devel.txt", "production.txt", "tests.txt"],
		"system_requirements": ["system_requirements.txt"],
		"locals_path": /path/to/your/requirements/on/local/machine/local.py",
		"branch": "master"
	}

The structure of custom Django settings file
--------------------------------------------

For better customization there is possibility to upload the file called
``local.py`` that can override some project parameters (for example in this
way you can disable page caching).
This file is uploaded during each deployment to the settings directory. It is
imported to the main Django settings file.

Example local settings file may look like the following:

::

	import os
	from defaults import DATABASES, PROJECT_PATH, ROOT_PATH

	MEDIA_ROOT = os.path.join(ROOT_PATH, 'media')
	STATIC_ROOT = os.path.join(PROJECT_PATH, 'collected_static')
	STATIC_URL = '/static/'

	TIME_ZONE = 'UTC'
	CACHE_BACKEND = 'dummy:///'

	DB = DATABASES['default']
	DATABASE_NAME = DB['NAME']
	DATABASE_USER = DB['USER']
	DATABASE_PASSWORD = DB['PASSWORD']

	MTURK_AUTH_EMAIL = 'user@email.com'
	MTURK_AUTH_PASSWORD = '******'

	USE_CACHE = True

Running the deployment script
-----------------------------

If all is already properly configured go to the deployment subdirectory:

::

	$ cd path/to/Mturk-Tracker/deployment/

and run the fabric script. The following command will install all requirements
(including Python and system packages):

::

	$ fab deploy:conf_file="path/to/site-name.json",setup_environment=True -H 127.0.0.1 -u user

or you may want to update only project source (for example in order to apply
changes from the repository):

::

	$ fab deploy:conf_file="path/to/site-name.json",requirements=False -H 127.0.0.1 -u user

For more information:

::

	$ fab help

A comprehensive description including webserver, database and crawler can be
found in documentation's section on deployment: (todo: it is not yet there)
http://mturk-tracker.com/documentation/mturk-tracker/ .

Manual setup
============

Required libraries
------------------

Mturk-Tracker requires a number of libraries that should be installed in the
operating system. The most recent and complete list can be found in
https://github.com/ipeirotis/Mturk-Tracker/tree/master/deployment/files/requirements/system_requirements.txt

To install the requirements simply type (for debian-like system):

    $ sudo apt-get install postgresql-9.1 postgresql-server-dev-9.1 git \
        subversion mercurial python2.7-dev libevent-dev openjdk-6-jdk

Python environment
------------------

There is a number of python dependencies required for the project to run, see
files in
https://github.com/ipeirotis/Mturk-Tracker/tree/master/deployment/files/requirements/.

The easiest way to install and manage python packages is by using pip for
installing packages and virtualenv_ for creating a separate virtual environment.
If using virtualenv, consider virtualenvwrapper packed for convenience.

First, create and activate new virtual python environment::

    $ virtualenv mturk --no-site-packages
    $ cd  mturk
    $ . bin/activate

or::

    $ mkvirtualenv mturk --no-site-packages
    $ workon mturk
    $ cd $VIRTUAL_ENV  # optional

if using virtualenvwrapper_.

TODO: Update the remainder of the guide.

After that, clone mturk code from repository and install all
dependencies using pip_ (you have to install *mercurial* and *subversion*
first, a mentioned in Required Libraries)::

	$ git clone https://github.com/ipeirotis/Mturk-Tracker.git
	$ cd src
	$ git fetch
	$ git checkout -b virtualenv --track origin/virtualenv
	$ echo "mturk.settings.base" > DJANGO_SETTINGS_MODULE
	$ pip install -r requirements.txt

Libraries update
~~~~~~~~~~~~~~~~

Because ``pip`` should take care of all libraries, use it to update already
existing configuration. Whenever new dependency appears, run ``pip -r
requirements.txt`` just to update.


Choosing custom settings module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default ``mturk.settings.defaults`` configuration module is being used. To add
custom variables you can add code to:

- ``mturk.settings.default`` - project default variables visible for all other
  configuration files

You can also setup any other configuration module by setting
``DJANGO_SETTINGS_MODULE`` shell variable or file as given in example above.


Setting up Database
~~~~~~~~~~~~~~~~~~~

Make sure that django app can connect to database, the best way to do that is to allow postgres to accept local connections by editing pg_hba.conf file.
Check if you can connect to database::

	$ psql -U postgres

In order to setup a clean db you have to create the database and populate it with tables::

	$ createdb -U postgres  mturk_tracker
	$ createlang plpgsql -U postgres -d mturk_tracker
	$ python manage.py syncdb
	$ python manage.py migrate

Running django appliaction
--------------------------

Nothing special, just type::

    $ sudo python manage.py runserver

in django project directory. And then point your browser to
http://localhost:8000/

Crawling mturk
--------------

You may launch initial crawl by::

	$ python manage.py crawl --workers=6 --logconf=logging.conf

Logs will be saved in ``/tmp/crawler.log``. Because mturk requires
authentication for HITs listings pagination, use ``--mturk-email`` and
``--mturk-password`` flags to authenticate and crawl as mturk worker.

To generate data that will be displayed on graphs you need to launch scripts::

	$ python manage.py db_refresh_mviews
	$ python manage.py db_update_agregates
	$ python manage.py db_calculate_daily_stats

Searching in collected crawls
-----------------------------

Mturk-Tracker gives ability for searching in mturk projects. Internally it
uses ``Django-haystack`` application which in turn uses ``Solr`` (in version
3.6.0) indexing server as a backend.

Solr setup
~~~~~~~~~~

Go to the Solr's page http://lucene.apache.org/solr/ for information on how to
obtain appropirate Solr release.

For proper Solr's core configuration simply copy directory
https://github.com/ipeirotis/Mturk-Tracker/tree/master/deployment/files/solr/solr/
to ``path/to/your/solr/`` and manually replace the following

::

    user="%(solr_db_user)s"
    password="%(solr_db_password)s"

with

::

    user="your_solr_db_user"
    password="your_solr_db_password"

in file ``path/to/your/solr/solr/en/conf/import_db_hits.xml`` (this is done
automatically in the case of automatic project setup). Next restart
Solr server and visit http://127.0.0.1:8983/solr/en/select?q= (an empty xml
response should be returned).

Populating the search index
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the Solr server is properly configured and some crawler data is generated
try to fill up the index with the following command

::

    python manage.py solr_data_import --verbose

You can also check Solr's status at any time. Simply type

::

    python manage.py solr_status


.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _virtualenvwrapper: http://www.doughellmann.com/projects/virtualenvwrapper/
.. _pip: http://pypi.python.org/pypi/pip
