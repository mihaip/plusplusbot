import api

class UpdateSet(object):
  def __init__(self):
    self._targets = []
    self._user_ids = []
  
  def IsEmpty(self):
    return len(self._targets) == 0 and len(self._user_ids) == 0
  
  def AddOp(self, op):
    target = op.target
    user = op.message.user
    
    # Target page must change
    if target not in self._targets:
      self._targets.append(target)
    
    # So must the page for the user that made it, if the op wasn't anonymous
    if not op.is_anonymous:
      self._AddUser(user)
      
      # And their friends' pages
      for friend in api.GetFriends(user):
        self._AddUser(friend)

  def _AddUser(self, user):
    user_id = user.id
    if user_id not in self._user_ids:
      self._user_ids.append(user_id)
      
  def GetTargets(self):
    return self._targets
    
  targets = property(GetTargets)

  def GetUserIds(self):
    return self._user_ids
    
  user_ids = property(GetUserIds)
    