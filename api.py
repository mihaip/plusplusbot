import rfc822
import time

import twitter

_api = None
_username = None
_password = None
_default_cache = None
_friends_filter = None

def Init(username, password, friends_filter):
  global _api
  global _default_cache
  
  global _username
  global _password
  global _friends_filter
  
  _api = twitter.Api()
  _default_cache = _api.GetCache()
  _api.SetCache(None)
  
  _username = username
  _password = password
  _friends_filter = friends_filter

_object_cache = {}
_OBJECT_CACHE_TIMEOUT = 60 * 60 * 24 # Keep user data cached for one day
_MAX_CACHE_TIMEOUT = 60 * 60 * 24 * 364 # Use stale data up to one year old

class ObjectCache(object):
  def __init__(self):
    self.Reset()
  
  def Reset(self):
    self.map = {}
    self.creation_time = time.time()
  
  def IsExpired(self):
    return time.time() - self.creation_time > _OBJECT_CACHE_TIMEOUT

def GetCachedContent(cache_id, generator_closure, key, fallback_value):
  if cache_id not in _object_cache:
    _object_cache[cache_id] = ObjectCache()
  
  cache = _object_cache[cache_id]
  
  # We first check in our own cache, which is beter than the API one since it
  # doesn't involve re-parsing JSON.
  # No need to have per-entry expiration times, clearing the whole cache once
  # a day is good enough.
  if cache.IsExpired():
    cache.Reset()

  if key in cache.map:
    return cache.map[key]

  # Otherwise temporarily restore caching behavior in the API
  _api.SetCache(_default_cache)
  _api.SetCacheTimeout(_OBJECT_CACHE_TIMEOUT)

  value = generator_closure()
  
  # If we couldn't load the data (perhaps because of rate limiting), we will
  # try again with a long cache timeout, to see if we have any stale data that
  # we can reuse
  if not value:
    _api.SetCacheTimeout(_MAX_CACHE_TIMEOUT)
    value = generator_closure()
  
  # If we still couldn't load the data (usually due to permission issues), we 
  # still cache the response so tha we don't keep re-fetching the URL
  if not value:
    value = fallback_value

  # Add it to our own cache
  cache.map[key] = value

  # Go back to no caching for subsequent API operations
  _api.SetCache(None)

  return value  

def ReloadUser(current_user):
  loaded_user = GetUser(current_user.id)
  return loaded_user or current_user

def GetUser(user_id, always_cache=False):
  return GetCachedContent('user', 
                          lambda: _api.GetUserInfo(_username, 
                                                   _password,
                                                   user_id,
                                                   always_cache=always_cache),
                          user_id,
                          None)  

def GetFriends(user):
  friends = GetCachedContent('friends',
                             lambda: _api.GetFriends(_username,
                                                     _password,
                                                     user.id),
                             user.id,
                             [])

  return filter(_friends_filter, friends)


def PostDirectMessage(user, text):                          
  return _api.PostDirectMessage(_username,
                                _password,
                                user,
                                text)
                         
def GetDirectMessages(since_seconds):
  return _api.GetDirectMessages(_username, 
                                _password,
                                since=rfc822.formatdate(since_seconds))

def GetFriendsTimeline(since_seconds):
  return _api.GetFriendsTimeline(
      _username,
      _password,
      since=since_seconds and rfc822.formatdate(since_seconds) or None)

def GetSingleStatus(id):
  return _api.GetSingleStatus(_username,
                              _password,
                              id)

def GetUrlFetchCount():
  return _api.GetUrlFetchCount();
  
def ResetUrlFetchCount():
  _api.ResetUrlFetchCount();