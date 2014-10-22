# -*- coding: utf-8 -*-
from BeautifulSoup import BeautifulSoup, ResultSet, Tag
from django.utils.encoding import smart_str
from utils.text import fuse, remove_whitespaces, strip_html

import datetime
import hashlib
import logging
import re
import sys
import traceback
import urllib2

from crawler_common import get_allhit_url, get_group_url, grab_error
from mturk.main.models import HitGroupContent

log = logging.getLogger(__name__)


##########################################################################################
# Fetches HIT group information from HITs list page by it's position in the pagination.
#
# In:
#  pages - list of page numbers
##########################################################################################
def callback_allhit(pages, **kwargs):

    if type(pages) != type([]):
        raise Exception('::callback_allhit() must be called with one list argument')

    def remove_newline_fields(list):
        while True:
            try:
                list.remove("\n")
            except:
                break
        return list
    
#    def is_soup(object):
#        soup = BeautifulSoup()
#        if type(object) == type(soup) or type(object) == type(ResultSet('')) or type(object) == type(Tag(soup, "div", [])):
#            return True
#        return False

    data = []
    errors = []

    # Processing every page
    for page_number in pages:
        try:
            # Downloading page
            log.info("Downloading page: %s" % page_number)
            page_url = get_allhit_url(page_number)
            log.debug("Downloading %s" % page_url)
            response = urllib2.urlopen(page_url)
            html = response.read()
            soup = BeautifulSoup(html)

            # Parsing HIT groups' list
            table = soup.find('table', cellpadding='0', cellspacing='5', border='0', width='100%')
            if type(table) == type(None):

                i = 0
                while i < 3:
                    log.warn("Soup returned an empty table for page %s. Trying once more" % page_number)
                    response = urllib2.urlopen(page_url)
                    html = response.read()
                    soup = BeautifulSoup(html)
                    table = soup.find('table', cellpadding='0', cellspacing='5', border='0', width='100%')
                    if type(table) != type(None):
                        break
                    else:
                        table = None
                        soup = None
                        html = None
                        i = i + 1

                if type(table) == type(None):
                    log.warn("Soup returned an empty table. This should not happen. Skipping page")
                    continue

            table.contents = remove_newline_fields(table.contents)

            # Parsing and fetching information about each group
            for i_group in range(0, len(table.contents)):
                log.debug("Processing group %s on page %s" % (i_group, page_number))
                try:
                    group_html = table.contents[i_group]

                    # Title
                    title = group_html.find('a', {'class':'capsulelink'})
                    if type(title) != type(None):
                        try:
                            title = str(title.contents[0])
                        except:
                            title = unicode(title.contents[0])
                        try:
                            title = unicode(remove_whitespaces(title))
                        except:
                            title = ''
                    
                    # Remove <span> in title
                    title = remove_whitespaces(strip_html(title))
                    
                    fields = group_html.findAll('td', {'align':'left','valign':'top','class':'capsule_field_text'})

                    if len(fields) == 7:

                        # Requester's name and ID
                        requester_html = remove_newline_fields(fields[0].contents)[0]
                        requester_name = remove_whitespaces(strip_html(unicode(requester_html.contents[0]))) # Remove <span> in requester name
                        requester_id = requester_html['href']
                        start = requester_id.index('requesterId=')+12
                        stop = requester_id.index('&state')
                        requester_id = requester_id[start:stop]

                        # HIT group expiration date
                        hit_expiration_date = remove_newline_fields(fields[1].contents)[0]
                        hit_expiration_date = remove_whitespaces(strip_html(hit_expiration_date))
                        hit_expiration_date = hit_expiration_date[:hit_expiration_date.index('(')-2]
                        hit_expiration_date = datetime.datetime.strptime(hit_expiration_date, '%b %d, %Y')

                        # Time alloted
                        time_alloted = remove_newline_fields(fields[2].contents)[0]
                        time_alloted = remove_whitespaces(strip_html(time_alloted))
                        time_alloted = int(time_alloted[:time_alloted.index(' ')])

                        # Reward
                        reward = float(remove_newline_fields(fields[3].contents)[0][1:])

                        # HITs available
                        hits_available = int(remove_newline_fields(fields[4].contents)[0])

                        # Description
                        description = unicode(remove_newline_fields(fields[5].contents)[0])

                        # Keywords
                        keywords_raw = remove_newline_fields(fields[6].contents)
                        keywords = []
                        for i in range(0, len(keywords_raw)):
                            try:
                                keyword = keywords_raw[i].contents[0]
                                keywords.append(keyword)
                            except:
                                continue
                        keywords = unicode(fuse(keywords, ','))

                        # Qualification
                        qualifications = ''
                        qfields = group_html.findAll('td', {'style':'padding-right: 2em; white-space: nowrap;'})

                        if len(qfields) > 0:
                            qfields = [remove_whitespaces(unicode(remove_newline_fields(qfield.contents)[0])) for qfield in qfields]
                            qualifications = fuse(qfields, ', ')
                        qfields = None

                        # Occurrence date
                        occurrence_date = datetime.datetime.now()

                        # Group ID
                        group_id = group_html.find('span', {'class':'capsulelink'})
                        group_id_hashed = False
                        if type(group_id) != type(None):
                            group_id = remove_newline_fields(group_id.contents)[0]
                            if 'href' in group_id._getAttrMap():
                                start = group_id['href'].index('groupId=')+8
                                stop = group_id['href'].index('&')
                                group_id = group_id['href'][start:stop]
                            else:
                                group_id_hashed = True
                                composition = "%s;%s;%s;%s;%s;%s;%s;" % (title,requester_id,
                                                                         time_alloted,reward,
                                                                         description,keywords,
                                                                         qualifications)
                                composition = smart_str(composition)
                                group_id = hashlib.md5(composition).hexdigest()

                        # Checking whether processed content is already stored in the database
                        hit_group_content = None
                        try:
                            log.debug("group_id=%s; requester=%s; title=%s; desc=%s; ta=%s; reward=%s" % (group_id, requester_id, title, description, time_alloted, reward))
                            hit_group_content = HitGroupContent.objects.get(group_id=group_id,
                                                                            requester_id=requester_id,
                                                                            title=title,
                                                                            description=description,
                                                                            time_alloted=time_alloted,
                                                                            reward=reward,
                                                                            )
                        except HitGroupContent.DoesNotExist:
                            hit_group_content = HitGroupContent(**{
                                    'title': title,
                                    'requester_id': requester_id,
                                    'requester_name': requester_name,
                                    'time_alloted': time_alloted,
                                    'reward': reward,
                                    'html': '',
                                    'description': description,
                                    'keywords': keywords,
                                    'qualifications': qualifications,
                                    'occurrence_date': occurrence_date,
                                    'group_id': group_id,
                                    'group_id_hashed': group_id_hashed
                                })

                        data.append({
                            'HitGroupStatus': {
                                'group_id': group_id,
                                'hits_available': hits_available,
                                'page_number': page_number,
                                'inpage_position': i_group+1,
                                'hit_expiration_date': hit_expiration_date,
                                'hit_group_content': hit_group_content
                            }
                        })

                    fields = None
                    group_html = None

                except:
                    log.error("Failed to process group %s on %s page (%s)" % (i_group, page_number, sys.exc_info()[0].__name__))
                    errors.append(grab_error(sys.exc_info()))
                    print grab_error(sys.exc_info())

            table = None
            soup = None
            html = None

        except:
            log.error("Failed to process page %d (%s)" % (page_number, sys.exc_info()[0].__name__))
            errors.append(grab_error(sys.exc_info()))
            print grab_error(sys.exc_info())

    return {'data':data,'errors':errors}

##########################################################################################
# Fetches html details for every HIT Group result record.
#
# In:
#  data - a result of callback_allhit
##########################################################################################
def callback_details(data, **kwargs):

    if type(data) != type([]):
        raise Exception, '::callback_allhit() must be called with one list argument'

    errors = []

    # Processing each record
    for i in range(0, len(data)):
        if data[i]['HitGroupStatus']['hit_group_content'].html != '': continue

        group_id = data[i]['HitGroupStatus']['group_id']
        if not data[i]['HitGroupStatus']['hit_group_content'].group_id_hashed:
            try:
                log.info("Downloading group details for: %s" % group_id)
                html = None

                # Downloading group details
                preview_html = urllib2.urlopen(get_group_url(group_id)).read()

                # Seeking for an iframe.
                iframe_url = re.search(re.compile(r"<iframe.*?src=\"(.*?)\""), preview_html)

                # Fetching iframe source if there is iframe in the html. Otherwise, the
                # the html must be already here in the <div id="hit-wrapper ...
                if iframe_url:
                    html = urllib2.urlopen(iframe_url.group(1)).read()
                else:
                    html = str(BeautifulSoup(preview_html).find('div', {'id':'hit-wrapper'}))

                if html:
                    data[i]['HitGroupStatus']['hit_group_content'].html = html

                preview_html = None

            except:
                log.error("Failed to process group details for %s (%s)" % (group_id,
                              sys.exc_info()[0].__name__))
                errors.append(grab_error(sys.exc_info()))
    return {'data':data,'errors':errors}

##########################################################################################
# Adds Crawl Model object to every HitGroupStatus. Must be called after fetching and
# analyzing the data.
#
# In:
#  data - a result of callback_allhit
##########################################################################################
def callback_add_crawlfk(data, **kwargs):

    if type(data) != type([]):
        raise Exception, '::callback_add_crawlfk() must be called with one list argument'

    if 'crawl' not in kwargs:
        raise Exception, '::callback_add_crawlfk() must be called with \'crawl_id\' kwarg being an id of Crawl'

    for i in range(0, len(data)):
        data[i]['HitGroupStatus']['crawl'] = kwargs['crawl']

    return {'data':data,'errors':[]}
