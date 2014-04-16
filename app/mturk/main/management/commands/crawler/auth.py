import cookielib
import re
import urllib
import urllib2

from django.conf import settings


AUTH_PAGE = '{}/mturk'.format(settings.MTURK_PAGE)


def install_opener():
    """Install global opener with cookies support."""
    jar = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
    # Amazon displays 'Please enable cookies (...)' without fake 'User-agent'
    # header.
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib2.install_opener(opener)
    return opener


def authenticate(email, password):
    """Authenticate using mturk worker account. This should be done after
    installation of opener with cookie support."""
    # It should redirect to form with hidden fields containing all necessary
    # tokens to authenticate.
    response = urllib2.urlopen('{}/beginsignin'.format(AUTH_PAGE))
    html = response.read()
    # Parse auth form fields.
    data = re.findall(r'input.+?name="(.+?)".+?value="(.+?)"', html)
    query = dict(data)
    query.update({
        'email': email,
        'password': password,
        'create': 0,  # Force password authentication.
    })
    return urllib2.urlopen(response.url, urllib.urlencode(query))
