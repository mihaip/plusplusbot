#!/usr/bin/python
#
# Copyright 2007 Google Inc. All Rights Reserved.

'''A library that provides a python interface to the Twitter API'''

__author__ = 'dewitt@google.com'
__version__ = '0.3'


import base64
import calendar
import datetime
import httplib
import md5
import os
import simplejson
import tempfile
import time
import urllib
import urllib2
import urlparse
import twitter

class TwitterError(Exception):
  '''Base class for Twitter errors'''


class Status(object):
  '''A class representing the Status structure used by the twitter API.

  The Status structure exposes the following properties:

    status.created_at
    status.created_at_in_seconds # read only
    status.id
    status.text
    status.relative_created_at # read only
    status.user
  '''
  def __init__(self,
               created_at=None,
               id=None,
               text=None,
               user=None,
               now=None):
    '''An object to hold a Twitter status message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      created_at: The time this status message was posted
      id: The unique id of this status message
      text: The text of this status message
      relative_created_at:
        A human readable string representing the posting time
      user:
        A twitter.User instance representing the person posting the message
      now:
        The current time, if the client choses to set it.  Defaults to the
        wall clock time.
    '''
    self.created_at = created_at
    self.id = id
    self.text = text
    self.user = user
    self.now = now

  def GetCreatedAt(self):
    '''Get the time this status message was posted.

    Returns:
      The time this status message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this status message was posted.

    Args:
      created_at: The time this status message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this status message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this status message was posted, in seconds since the epoch.

    Returns:
      The time this status message was posted, in seconds since the epoch.
    '''
    try:
      parsed = time.strptime(self.created_at, '%a %b %d %H:%M:%S +0000 %Y')
    except ValueError:
      try:
        print 'incorrect date format 1: "%s"' % self.created_at
        parsed = time.strptime(self.created_at, '%a %d %b %H:%M:%S +0000 %Y')
      except ValueError:
        print 'incorrect date format 2: "%s"' % self.created_at
        parsed = time.strptime(self.created_at, '%m/%d/%Y %H:%M:%S %Z')
    
    return calendar.timegm(parsed)

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this status message was "
                                       "posted, in seconds since the epoch")

  def GetCreatedAtDateTime(self):
    return datetime.datetime.utcfromtimestamp(self.GetCreatedAtInSeconds())
    
  created_at_datetime = property(GetCreatedAtDateTime)
    

  def GetId(self):
    '''Get the unique id of this status message.

    Returns:
      The unique id of this status message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this status message.

    Args:
      id: The unique id of this status message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this status message.')

  def GetText(self):
    '''Get the text of this status message.

    Returns:
      The text of this status message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this status message.

    Args:
      text: The text of this status message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this status message')

  def GetRelativeCreatedAt(self):
    '''Get a human redable string representing the posting time

    Returns:
      A human readable string representing the posting time
    '''
    fudge = 1.25
    delta  = int(self.now) - int(self.created_at_in_seconds)

    if delta < (1 * fudge):
      return 'about a second ago'
    elif delta < (60 * (1/fudge)):
      return 'about %d seconds ago' % (delta)
    elif delta < (60 * fudge):
      return 'about a minute ago'
    elif delta < (60 * 60 * (1/fudge)):
      return 'about %d minutes ago' % (delta / 60)
    elif delta < (60 * 60 * fudge):
      return 'about an hour ago'
    elif delta < (60 * 60 * 24 * (1/fudge)):
      return 'about %d hours ago' % (delta / (60 * 60))
    elif delta < (60 * 60 * 24 * fudge):
      return 'about a day ago'
    else:
      return 'about %d days ago' % (delta / (60 * 60 * 24))

  relative_created_at = property(GetRelativeCreatedAt,
                                 doc='Get a human readable string representing'
                                     'the posting time')
  
  def GetUser(self):
    '''Get a twitter.User reprenting the entity posting this status message.

    Returns:
      A twitter.User reprenting the entity posting this status message
    '''
    return self._user

  def SetUser(self, user):
    '''Set a twitter.User reprenting the entity posting this status message.

    Args:
      user: A twitter.User reprenting the entity posting this status message
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='A twitter.User reprenting the entity posting this '
                      'status message')

  def GetNow(self):
    '''Get the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.
    
    Returns:
      Whatever the status instance believes the current time to be,
      in seconds since the epoch.
    '''
    if self._now is None:
      self._now = calendar.timegm(time.gmtime())
    return self._now

  def SetNow(self, now):
    '''Set the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Args:
      now: The wallclock time for this instance.
    '''
    self._now = now

  now = property(GetNow, SetNow,
                 doc='The wallclock time for this status instance.')

  
  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.created_at == other.created_at and \
             self.id == other.id and \
             self.text == other.text and \
             self.user == other.user
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.Status instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.Status instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.Status instance.

    Returns:
      A JSON string representation of this twitter.Status instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.Status instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.Status instance
    '''
    data = {}
    if self.created_at:
      data['created_at'] = self.created_at
    if self.id:
      data['id'] = self.id
    if self.text:
      data['text'] = self.text
    if self.user:
      data['user'] = self.user.AsDict()
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.Status instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    elif 'sender_screen_name' in data and 'sender_id' in data:
      user = User(id=data.get('sender_id'),
                  screen_name=data.get('sender_screen_name'))
    else:
      user = None
    return Status(created_at=data.get('created_at', None),
                  id=data.get('id', None),
                  text=data.get('text', None),
                  user=user)


class User(object):
  '''A class representing the User structure used by the twitter API.

  The User structure exposes the following properties:

    user.id
    user.name
    user.screen_name
    user.location
    user.description
    user.profile_image_url
    user.url
    user.status
  '''
  def __init__(self,
               id=None,
               name=None,
               screen_name=None,
               location=None,
               description=None,
               profile_image_url=None,
               url=None,
               status=None):
    self.id = id
    self.name = name
    self.screen_name = screen_name
    self.location = location
    self.description = description
    self.profile_image_url = profile_image_url
    self.url = url
    self.status = status


  def GetId(self):
    '''Get the unique id of this user.

    Returns:
      The unique id of this user
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this user.

    Args:
      id: The unique id of this user.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this user.')

  def GetName(self):
    '''Get the real name of this user.

    Returns:
      The real name of this user
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this user.

    Args:
      name: The real name of this user
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this user.')

  def GetScreenName(self):
    '''Get the short username of this user.

    Returns:
      The short username of this user
    '''
    return self._screen_name

  def SetScreenName(self, screen_name):
    '''Set the short username of this user.

    Args:
      screen_name: the short username of this user
    '''
    self._screen_name = screen_name

  screen_name = property(GetScreenName, SetScreenName,
                         doc='The short username of this user.')

  def GetLocation(self):
    '''Get the geographic location of this user.

    Returns:
      The geographic location of this user
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geographic location of this user.

    Args:
      location: The geographic location of this user
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geographic location of this user.')

  def GetDescription(self):
    '''Get the short text description of this user.

    Returns:
      The short text description of this user
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the short text description of this user.

    Args:
      description: The short text description of this user
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The short text description of this user.')

  def GetUrl(self):
    '''Get the homepage url of this user.

    Returns:
      The homepage url of this user
    '''
    return self._url

  def SetUrl(self, url):
    '''Set the homepage url of this user.

    Args:
      url: The homepage url of this user
    '''
    self._url = url

  url = property(GetUrl, SetUrl,
                 doc='The homepage url of this user.')

  def GetProfileImageUrl(self):
    '''Get the url of the thumbnail of this user.

    Returns:
      The url of the thumbnail of this user
    '''
    return self._profile_image_url

  def SetProfileImageUrl(self, profile_image_url):
    '''Set the url of the thumbnail of this user.

    Args:
      profile_image_url: The url of the thumbnail of this user
    '''
    self._profile_image_url = profile_image_url

  profile_image_url= property(GetProfileImageUrl, SetProfileImageUrl,
                              doc='The url of the thumbnail of this user.')

  def GetProfileMiniImageUrl(self):
    if not self._profile_image_url or \
       self._profile_image_url.find("images/default_image.gif") != -1:
      return "http://assets0.twitter.com/images/default_profile_image_mini.gif"
    else:
      return self._profile_image_url.replace("normal", "mini")

  profile_mini_image_url = property(GetProfileMiniImageUrl)

  def GetStatus(self):
    '''Get the latest twitter.Status of this user.

    Returns:
      The latest twitter.Status of this user
    '''
    return self._status

  def SetStatus(self, status):
    '''Set the latest twitter.Status of this user.

    Args:
      status: The latest twitter.Status of this user
    '''
    self._status = status

  status = property(GetStatus, SetStatus,
                  doc='The latest twitter.Status of this user.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.screen_name == other.screen_name and \
             self.location == other.location and \
             self.description == other.description and \
             self.profile_image_url == other.profile_image_url and \
             self.url == other.url and \
             self.status == other.status
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.User instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.User instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.User instance.

    Returns:
      A JSON string representation of this twitter.User instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.User instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.User instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.screen_name:
      data['screen_name'] = self.screen_name
    if self.location:
      data['location'] = self.location
    if self.description:
      data['description'] = self.description
    if self.profile_image_url:
      data['profile_image_url'] = self.profile_image_url
    if self.url:
      data['url'] = self.url
    if self.status:
      data['status'] = self.status.AsDict()
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.User instance
    '''
    if 'status' in data:
      status = Status.NewFromJsonDict(data['status'])
    else:
      status = None
    return User(id=data.get('id', 0),
                name=data.get('name', None),
                screen_name=data.get('screen_name', None),
                location=data.get('location', None),
                description=data.get('description', None),
                profile_image_url=data.get('profile_image_url', None),
                url=data.get('url', None),
                status=status)


class Api(object):
  '''A python interface into the Twitter API

  By default, the Api caches results for 1 minute.

  Example usage:

    To create an instance of the twitter.Api class:

      >>> import twitter
      >>> api = twitter.Api()

    To fetch the most recently posted public twitter status messages:

      >>> statuses = api.GetPublicTimeline()
      >>> print [s.user.name for s in statuses]
      [u'DeWitt', u'Kesuke Miyagi', u'ev', u'Buzz Andersen', u'Biz Stone'] #...

    To fetch a single user's public status messages, where "user" is either
    a Twitter "short name" or their user id.

      >>> statuses = api.GetUserTimeline(user)
      >>> print [s.text for s in statuses]

    To fetch a list a user's friends:

      >>> users = api.GetFriends(username, password)
      >>> print [u.name for u in users]

    To post a twitter status message:

      >>> status = api.PostUpdate(username, password, 'I love python-twitter!')
      >>> print status.text
      I love python-twitter!
  '''

  DEFAULT_CACHE_TIMEOUT = 60 # cache for 1 minute

  _API_REALM = 'Twitter API'

  def __init__(self):
    '''Instantiate a new twitter.Api object.'''
    self._cache = _FileCache()
    self._urllib = urllib2
    self._url_fetch_count = 0
    self._cache_timeout = Api.DEFAULT_CACHE_TIMEOUT
    self._user_agent = 'Python-urllib/%s (python-twitter/%s)' % \
                       (self._urllib.__version__, twitter.__version__)

  def GetPublicTimeline(self):
    '''Fetch the sequnce of public twitter.Status message for all users.

    Returns:
      An sequence of twitter.Status instances, one for each message
    '''
    url = 'http://twitter.com/statuses/public_timeline.json'
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetUserTimeline(self, user, count=None):
    '''Fetch the sequence of public twitter.Status messages for a single user.

    Args:
      user:
        either the username (short_name) or id of the user to retrieve
      count: the number of status messages to retrieve

    Returns:
      A sequence of twitter.Status instances, one for each message up to count
    '''
    try:
      if count:
        int(count)
    except:
      raise TwitterError("Count must be an integer")
    if count:
      parameters = {'count':count}
    else:
      parameters = {}
    url = 'http://twitter.com/t/status/user_timeline/%s' % user
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetFriendsTimeline(self, username, password, since=None):
    '''Fetch the sequence of twitter.Status messages for a user\'s friends

    Args:
      username: The username to be fetched
      password: The password for the username to be fetched.

    Returns:
      A sequence of twitter.Status instances, one for each message
    '''
    url = 'http://twitter.com/statuses/friends_timeline.json'
    if since:
      parameters = {"since": since}
    else:
      parameters = {}
    json = self._FetchUrl(url,
                          username=username,
                          password=password,
                          parameters=parameters)
    if json:                          
      try:
        data = simplejson.loads(json)
      except ValueError:
        return []
      return [Status.NewFromJsonDict(x) for x in data]
    else:
      return []

  def GetDirectMessages(self, username, password, since=None):
    url = 'http://twitter.com/direct_messages.json'
    if since:
      parameters = {"since": since}
    else:
      parameters = {}
    json = self._FetchUrl(url, 
                          username=username,
                          password=password,
                          parameters=parameters)
    if json:
      try:
        data = simplejson.loads(json)
      except ValueError:
        return []
      return [Status.NewFromJsonDict(x) for x in data]
    else:
      return []

  def GetSingleStatus(self, username, password, id):
    url = 'http://twitter.com/statuses/show/%d.json' % id
    json = self._FetchUrl(url, username=username, password=password)
    data = simplejson.loads(json)
    return Status.NewFromJsonDict(data)

  def GetFriends(self, username, password, user_id=None):
    '''Fetch the sequence of twitter.User instances, one for each friend

    Args:
      username: The username whose friends should be fetched
      password: The password for the username to be fetched.

    Returns:
      A sequence of twitter.User instances, one for each friend
    '''
    if user_id:
      url = 'http://twitter.com/statuses/friends/%s.json' % user_id
    else:
      url = 'http://twitter.com/statuses/friends.json'
    json = self._FetchUrl(url, username=username, password=password)
    try:
      data = simplejson.loads(json)
      return [User.NewFromJsonDict(x) for x in data]
    except:
      return None

  def GetFollowers(self, username, password):
    '''Fetch the sequence of twitter.User instances, one for each follower

    Args:
      username: The username whose followers should be fetched
      password: The password for the username to be fetched.

    Returns:
      A sequence of twitter.User instances, one for each follower
    '''
    url = 'http://twitter.com/statuses/followers.json'
    json = self._FetchUrl(url, username=username, password=password)
    data = simplejson.loads(json)
    return [User.NewFromJsonDict(x) for x in data]

  def GetUserInfo(self, username, password, user_id, always_cache=False):
    url = 'http://twitter.com/users/show/%s.json' % user_id
    json = self._FetchUrl(url, 
                          username=username, 
                          password=password,
                          always_cache=always_cache)
  
    try:
      data = simplejson.loads(json)
      return User.NewFromJsonDict(data)
    except:
      return None

  def PostUpdate(self, username, password, text):
    '''Post a twitter status message.

    Args:
      username: The username to post the status message
      password: The password for the username to be posted
      text: The message text to be posted

    Returns:
      A twitter.Status instance representing the message posted
    '''
    url = 'http://twitter.com/statuses/update.json'
    post_data = 'status=%s' % urllib.quote_plus(text)
    json = self._FetchUrl(url,
                          post_data=post_data,
                          username=username,
                          password=password,
                          no_cache=True)
    data = simplejson.loads(json)
    return Status.NewFromJsonDict(data)

  def PostDirectMessage(self, username, password, recipient, text):
    url = 'http://twitter.com/direct_messages/new.json'
    text = unicode(text).encode("utf-8")
    post_data = 'user=%d&text=%s' % (recipient.id,
                                     urllib.quote_plus(text))

    json = self._FetchUrl(url,
                          post_data=post_data,
                          username=username,
                          password=password,
                          no_cache=True)

    data = simplejson.loads(json)
    return Status.NewFromJsonDict(data)  

  def SetCache(self, cache):
    '''Override the default cache.  Set to None to prevent caching.

    Args:
      cache: an instance that supports the same API as the  twitter._FileCache
    '''
    self._cache = cache

  def GetCache(self):
    return self._cache

  def SetUrllib(self, urllib):
    '''Override the default urllib implementation.

    Args:
      urllib: an instance that supports the same API as the urllib2 module
    '''
    self._urllib = urllib

  def SetCacheTimeout(self, cache_timeout):
    '''Override the default cache timeout.

    Args:
      cache_timeout: time, in seconds, that responses should be reused.
    '''
    self._cache_timeout = cache_timeout

  def SetUserAgent(self, user_agent):
    '''Override the default user agent

    Args:
      user_agent: a string that should be send to the server as the User-agent
    '''
    self._user_agent = user_agent

  def _BuildUrl(self, url, path_elements=None, extra_params=None):
    # Break url into consituent parts
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

    # Add any additional path elements to the path
    if path_elements:
      # Filter out the path elements that have a value of None
      p = [i for i in path_elements if i]
      if not path.endswith('/'):
        path += '/'
      path += '/'.join(p)

    # Add any additional query parameters to the query string
    if extra_params and len(extra_params) > 0:
      # Filter out the parameters that have a value of None (but '' is okay)
      p = dict([ (k, v) for k, v in extra_params.items() if v is not None])
      # Convert the parameters into key=value&key=value form
      extra_query = urllib.urlencode(p)
      # Add it to the existing query
      if query:
        query += '&' + extra_query
      else:
        query = extra_query

    # Return the rebuilt URL
    return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))


  def _GetOpener(self, url, username=None, password=None):
    # Handle 304's by adding an error handler
    opener = self._urllib.build_opener(DefaultErrorHandler())
    headers = []
    
    # If requested, pass in the headers too. The proper way would be to add an 
    # authentication handler (see HTTPBasicAuthHandler), but in some cases,
    # instead of responding with a 401 challenge, Twitter will just return an
    # empty response (e.g. for a user that has made his list of updates be
    # friends-only, querying his/her list of friends will just return an empty
    # list)
    if username and password:
      encoded_credentials = \
          base64.encodestring('%s:%s' % (username, password))[:-1]
      auth_header =  "Basic %s" % encoded_credentials
      headers.append(("Authorization", auth_header))
    
    headers.append(('User-agent', self._user_agent))

    opener.addheaders = headers

    return opener


  def _FetchUrl(self,
                url,
                post_data=None,
                parameters=None,
                username=None,
                password=None,
                no_cache=None,
                always_cache=False):
    """Fetch a URL, optionally caching for a specified time.

    Args:
      url: The URL to retrieve
      post_data: A string to be sent in the body of the request. [OPTIONAL]
      parameters: A dict of key/value pairs that should added to
                  the query string. [OPTIONAL]
      username: A HTTP Basic Auth username for this request
      username: A HTTP Basic Auth password for this request
      no_cache: If true, overrides the cache on the current request

    Returns:
      A string containing the body of the response.
    """
    # Add key/value parameters to the query string of the url
    url = self._BuildUrl(url, extra_params=parameters)

    # Open and return the URL immediately if we're not going to cache
    if no_cache or not self._cache or not self._cache_timeout:
      opener = self._GetOpener(url, username=username, password=password)
      url_data = self._OpenUrl(opener, url, post_data)
    else:
      key = self._GetCacheKey(url, username)

      # See if it has been cached before
      last_cached = self._cache.GetCachedTime(key)

      # If the cached version is outdated then fetch another and store it
      if not last_cached or time.time() >= last_cached + self._cache_timeout:
        opener = self._GetOpener(url, username=username, password=password)
        url_data = self._OpenUrl(opener, 
                                 url, 
                                 post_data,
                                 always_cache=always_cache)
        
        # Don't cache 304's and errors
        if url_data:
          # Also make sure that we have valid JSON (for now all response are
          # JSON)
          try:
            data = simplejson.loads(url_data)
            self._cache.Set(key, url_data)
          except:
            if always_cache:
              self._cache.Set(key, url_data)
            pass
      else:
        url_data = self._cache.Get(key)

    # Always return the latest version
    return url_data
  
  def _GetCacheKey(self, url, username):
    # Unique keys are a combination of the url and the username
    if username:
      return username + ':' + url
    else:
      return url
  
  def _RemoveFromCache(self, url, username):
    key = self._GetCacheKey(url, username)
    
    if self._cache.GetCachedTime(key):
      print "removing %s from cache" % key
      self._cache.Remove(key)
  
  def _OpenUrl(self, opener, url, post_data, always_cache=False):
    print "fetching %s" % url
    self._url_fetch_count += 1 
    try:
      result = opener.open(url, post_data)
      
      if not always_cache:
        if hasattr(result, 'status'):
          status = result.status
          if status is 304 or status >= 400:
            return None
      
      return result.read()      
    except:
      return None
  
  def GetUrlFetchCount(self):
    return self._url_fetch_count
  
  def ResetUrlFetchCount(self):
    self._url_fetch_count = 0

class _FileCacheError(Exception):
  '''Base exception class for FileCache related errors'''

class _FileCache(object):

  DEFAULT_ROOT_DIRECTORY = os.path.join(tempfile.gettempdir(), 'python.cache')

  DEPTH = 3

  def __init__(self,root_directory=None):
    self._InitializeRootDirectory(root_directory)

  def Get(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return open(path).read()
    else:
      return None

  def Set(self,key,data):
    path = self._GetPath(key)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
      os.makedirs(directory)
    if not os.path.isdir(directory):
      raise _FileCacheError('%s exists but is not a directory' % directory)
    temp_fd, temp_path = tempfile.mkstemp()
    temp_fp = os.fdopen(temp_fd, 'w')
    temp_fp.write(data)
    temp_fp.close()
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory))
    os.rename(temp_path, path)

  def Remove(self,key):
    path = self._GetPath(key)
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory ))
    if os.path.exists(path):
      os.remove(path)

  def GetCachedTime(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return os.path.getmtime(path)
    else:
      return None

  def _InitializeRootDirectory(self, root_directory):
    if not root_directory:
      root_directory = _FileCache.DEFAULT_ROOT_DIRECTORY
    root_directory = os.path.abspath(root_directory)
    if not os.path.exists(root_directory):
      os.mkdir(root_directory)
    if not os.path.isdir(root_directory):
      raise _FileCacheError('%s exists but is not a directory' %
                            root_directory)
    self._root_directory = root_directory

  def _GetPath(self,key):
    if type(key) is unicode:
      key = key.encode('utf-8')
    hashed_key = md5.new(key).hexdigest()
    return os.path.join(self._root_directory,
                        self._GetPrefix(hashed_key),
                        hashed_key)

  def _GetPrefix(self,hashed_key):
    return os.path.sep.join(hashed_key[0:_FileCache.DEPTH])

class DefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):
  def http_error_default(self, req, fp, code, msg, headers):
    result = urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)
    print "status code: %d" % code
    result.status = code
    return result