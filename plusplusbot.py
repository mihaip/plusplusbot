#!/usr/local/bin/python
# coding=utf-8

import csv
import getopt
import md5
import re
import os.path
import socket
import sys
import time

import twitter

import api
import templates
import paths
import updateset
from util import *

DIRECT_LOG_NAME = "direct.csv"
FRIENDS_LOG_NAME = "friends.csv"

TARGET_BLACKLIST = [
  u'c'
]

_processed_messages = {}

class Op(object):
  def __init__(self, target, delta, reason, message, is_anonymous, is_direct):
    self.target = target.lower().replace(os.path.sep, '-')
    self.delta = delta
    self.reason = reason
    self.message = message
    self.is_anonymous = is_anonymous
    self.is_direct = is_direct
    self._id = None
    
    if not self.message.user.profile_image_url:
      self.message.user = api.ReloadUser(self.message.user)
    
    self.message_url = ("http://twitter.com/%s/statuses/%d" % 
        (message.user.screen_name, message.id))

  DICT_FIELD_NAMES = [
      "target", "delta", "reason", "message_id", "text", "sender_id", 
      "sender_screen_name", "created_at", "is_anonymous", "is_direct"
  ]
  
  def Equals(self, other_op):
    return self.target == other_op.target
  
  def GetTimestamp(self):
    return self.message.created_at_in_seconds

  timestamp = property(GetTimestamp)
  
  def GetId(self):
    if not self._id:
      m = md5.new()
      m.update(str(self.message.id))
      m.update(unicode(self.target).encode('utf-8'))
      m.update(unicode(self.reason).encode('utf-8'))
      self._id = m.hexdigest()

    return self._id

  id = property(GetId)
  
  def AsDict(self):
    return {
      "target": self.target,
      "delta": self.delta,
      "reason": self.reason,
      "message_id": self.message.id,
      "text": self.message.text,
      "sender_id": self.message.user.id,
      "sender_screen_name": self.message.user.screen_name,
      "created_at": self.message.created_at,
      "is_anonymous": self.is_anonymous,
      "is_direct": self.is_direct
    }
    
  @staticmethod
  def NewFromDict(dict):
    user = twitter.User(id=int(dict["sender_id"]),
                        screen_name=dict["sender_screen_name"])
    message = twitter.Status(created_at=dict["created_at"],
                             id=int(dict["message_id"]),
                             text=dict["text"],
                             user=user)
    return Op(target=dict["target"],
              delta=int(dict["delta"]),
              reason=dict["reason"],
              message=message,
              is_anonymous=dict["is_anonymous"] == "True",
              is_direct=dict.get("is_direct", "False") == "True")

  @staticmethod
  def TimeCompare(a, b):
    return int(a.timestamp - b.timestamp)

def LogOps(ops, log_name):
  Debug("%d new ops in the %s log" % (len(ops), log_name))
  
  file = open(paths.GetLogPath(log_name), "a")
  
  writer = UnicodeDictWriter(file, Op.DICT_FIELD_NAMES)
  
  for op in ops:
    writer.writerow(op.AsDict())
  
  file.close()

def GetOpsFromLog(log_name):
  path = paths.GetLogPath(log_name)
  if not os.path.exists(path): return []
  
  file = open(path, "r")
  
  reader = UnicodeDictReader(file, Op.DICT_FIELD_NAMES)
  
  ops = []

  for op_dict in reader:
    op = Op.NewFromDict(op_dict)
    ops.append(op)
    _processed_messages[op.message.id] = True
  
  file.close()
  
  ops.sort(Op.TimeCompare)
  
  Debug("Loaded %d ops from %s log" % (len(ops), log_name))
  return ops
  
def ExtractOps(messages, are_direct):
  DebugPush()
  
  ops = []
  
  for m in messages:
    # Guard against processing the same message more than once
    if m.id in _processed_messages:
      Debug("Skipping message %s since it's been processed before" % m.id)
      continue

    op_pieces = ExtractOpPieces(m.text)
    
    for (target, delta, reason, is_anonymous) in op_pieces:
      op = Op(target=target, 
              delta=delta, 
              reason=reason, 
              message=m, 
              is_anonymous=is_anonymous,
              is_direct=are_direct)

      if op.target in TARGET_BLACKLIST: continue

      ops.append(op)
      _processed_messages[op.message.id] = True    
  
  ops.sort(Op.TimeCompare)
  
  DebugPop()
  
  return ops    

def ExtractOpPieces(text):
  op_pieces = []
  text = (text.strip().replace("\n", " ")
                      .replace("\r", " ")
                      .replace(u"。", u"。 "))
  
  # Look for a leading exclamation mark as a sign that the message should
  # be considered anonymous (applies to all ops within it)
  is_anonymous = False
  if text.find("!") == 0:
    is_anonymous = True
    text = text[1:].strip()
  
  last_op_start = end = len(text)
  done = False
  
  # Find all the increments/decrements in the message, working from the back
  # to the front
  while not done:
    # Find the last increment/decrement 
    plus_index = text.rfind("++", 0, end)
    minus_index = text.rfind("--", 0, end)
    
    # See whichever one is later
    if plus_index is -1 and minus_index is -1:
      break
    if plus_index is -1:
      index = minus_index
    elif minus_index is -1:
      index = plus_index
    elif plus_index > minus_index:
      index = plus_index
    else:
      index = minus_index
    
    # Figure out which one we found
    if index is plus_index:
      delta = 1
    else:
      delta = -1
    
    # The reason is from there to the end
    reason = text[index + 2:last_op_start].strip()
    
    # When using parentheses, the target can have spaces in it
    target_start = -1
    if text[index - 1] == ')':
      target_start = text.rfind("(", 0, index)
    
    # Otherwise it's through the 
    if target_start == -1:
      target_start = text.rfind(" ", 0, index)
      if target_start == -1:
        target_start = 0
      else:
        target_start += 1
    
    target = text[target_start:index].strip()
    
    # If there is no target, then it's just a standalone plusplus or
    # minusminus, so we skip over it
    if target:
      # Remove parentheses from multi-word targets
      if target[0] == '(' and target[-1] == ')':
        target = target[1:-1]

      op_pieces.append((target, delta, reason, is_anonymous))
      
    if target_start is 0:
      done = True
    else:
      end = target_start - 1
    
    if target:
      last_op_start = end

  return op_pieces  

# Global maps/lists
scores_by_target = {}
recent_ops = []

# Variants of maps above with an additional segmentation by user id
scores_by_user_id_and_target = {}
recent_ops_by_user_id = {}

LANDING_PAGE_RECENT_OP_COUNT = 50
USER_PAGE_RECENT_OP_COUNT = 25

def GetMostActiveUsers():
  user_ids_to_scores = {}
  
  for user_id in scores_by_user_id_and_target.keys():
    score = Score(user_id)
    
    for target in scores_by_user_id_and_target[user_id].keys():
      score.Merge(scores_by_user_id_and_target[user_id][target])
    
    user_ids_to_scores[user_id] = score
  
  user_ids = user_ids_to_scores.keys()
  
  user_ids.sort(lambda a, b: Score.OpCountCompare(user_ids_to_scores[a],
                                                  user_ids_to_scores[b]),
                reverse=True)

  scores = [user_ids_to_scores[user_id] for user_id in user_ids[0:10]]
  
  return scores

class Score(object):
  def __init__(self, target):
    self.target = target
    self.score = 0
    self.ops = []
  
  def AddOp(self, op):
    self.ops.append(op)
    self.score += op.delta

  def GetDisplayOps(self):
    display_ops = self.ops
    
    display_ops.sort(Op.TimeCompare, reverse=True)
    
    return display_ops

  display_ops = property(GetDisplayOps)

  def GetRecentOps(self):
    ops = self.GetDisplayOps()
    if len(ops) > USER_PAGE_RECENT_OP_COUNT:
      ops = ops[0:USER_PAGE_RECENT_OP_COUNT]

    return ops

  recent_ops = property(GetRecentOps)

  def GetIncrementCount(self):
    return reduce(lambda sum, op: sum + (op.delta == 1 and 1 or 0), 
                  self.ops,
                  0)

  increment_count = property(GetIncrementCount)

  def GetDecrementCount(self):
    return reduce(lambda sum, op: sum + (op.delta == -1 and 1 or 0), 
                  self.ops,
                  0)

  decrement_count = property(GetDecrementCount)
  
  def GetTopUsers(self, is_negative):
    scores_by_user_id = {}
    
    for op in self.ops:
      if op.is_anonymous: continue
      
      user_id = op.message.user.id
      
      if user_id not in scores_by_user_id:
        scores_by_user_id[user_id] = Score(self)
      
      scores_by_user_id[user_id].AddOp(op)

    user_ids = scores_by_user_id.keys()
    
    user_ids.sort(lambda a, b: Score.ScoreCompare(scores_by_user_id[a],
                                                  scores_by_user_id[b]),
                  reverse=is_negative)
    
    scores = [scores_by_user_id[user_id] for user_id in user_ids]
    scores.reverse()
    return scores[0:10]

  def Merge(self, score):
    for op in score.ops:
      self.AddOp(op)
  
  @staticmethod
  def ScoreCompare(a, b):
    return a.score - b.score

  @staticmethod
  def OpCountCompare(a, b):
    return len(a.ops) - len(b.ops)

def AddOpToScoreMap(op, score_map):
  if op.target not in score_map:
    score = Score(op.target)
    score_map[op.target] = score
  else:
    score = score_map[op.target]
  
  score.AddOp(op)

def AddOpToRecentOps(op, recent_ops, op_count):
  add_op = False    
  # We may receive ops out of order, so make sure it's older than the oldest 
  # recent op
  if len(recent_ops) == op_count:
    oldest_op = recent_ops[-1]
    if oldest_op.timestamp < op.timestamp:
      recent_ops.remove(oldest_op)
      add_op = True
  else:
    add_op = True

  if add_op:
    # Insert op at the correct location
    inserted = False
    for i in range(0, len(recent_ops)):
      if op.timestamp > recent_ops[i].timestamp:
        recent_ops.insert(i, op)
        inserted = True
        break
    if not inserted:
      recent_ops.append(op)
  
def ProcessOps(ops, update_set):
  Debug("Processing %d ops" % len(ops))
  
  for op in ops:
    update_set.AddOp(op)
    
    AddOpToScoreMap(op, scores_by_target)
    AddOpToRecentOps(op, recent_ops, op_count=LANDING_PAGE_RECENT_OP_COUNT)
    
    # Record users
    if not op.is_anonymous:
      user_id = op.message.user.id
      if user_id not in scores_by_user_id_and_target:
        scores_by_user_id_and_target[user_id] = {}
        recent_ops_by_user_id[user_id] = []

      AddOpToScoreMap(op, scores_by_user_id_and_target[user_id])
      AddOpToRecentOps(op, 
                       recent_ops_by_user_id[user_id],
                       op_count=USER_PAGE_RECENT_OP_COUNT)

def AcknowledgeOps(api, ops):
  Debug("Sending op acknowledgements...")
  DebugPush()
  for op in ops:
    Debug("Ack'ing '%s' by %s" % (op.message.text, 
                                  op.message.user.screen_name))

    ack_text = "got your %s! \"%s\" is now at %d" % (
        op.delta == -1 and "minusminus" or "plusplus",
        op.target,
        scores_by_target[op.target].score)
    
    api.PostDirectMessage(op.message.user,
                          ack_text)
  DebugPop()

def GetScoresTops(scores):
  scores.sort(Score.ScoreCompare)
  
  bottom_10 = [s for s in scores[0:10] if s.score < 0]
  top_10 = [s for s in scores[len(scores)-10:len(scores)] if s.score >= 0]
  top_10.reverse()
  
  return (bottom_10, top_10)

def GetScoresCounts(scores):
  plusplus_count = 0
  minusminus_count = 0
  target_count = len(scores)
  user_ids = []
  
  for score in scores:
    for op in score.ops:
      if op.delta == -1:
        minusminus_count += 1
      else:
        plusplus_count += 1
    
      if not op.is_anonymous:
        user_id = op.message.user.id
        if user_id not in user_ids:
          user_ids.append(user_id)
  
  return (plusplus_count, minusminus_count, target_count, len(user_ids))

def GetScoresWithFriends(user, friends):
  total_friends = []
  total_friends.extend(friends)
  total_friends.append(user)
  
  scores_by_target = {}
  
  for friend in total_friends:
    # Not all friends may use plusplusbot.com
    if friend.id not in scores_by_user_id_and_target: continue
    
    scores = scores_by_user_id_and_target[friend.id]
    for score in scores.values():
      if score.target not in scores_by_target:
        scores_by_target[score.target] = Score(score.target)
      scores_by_target[score.target].Merge(score)

  return scores_by_target

def UpdateOutput(update_set):
  templates.ResetWriteLog()
  
  # Always write landing page
  
  DebugPush()
  
  Debug("Generating landing page")
  scores = scores_by_target.values()

  (bottom_10, top_10) = GetScoresTops(scores)
  most_active_users = GetMostActiveUsers()
  (plusplus_count, minusminus_count, target_count, user_count) = \
      GetScoresCounts(scores)  

  templates.Write(
      templates.LandingPageTemplate(bottom_10=bottom_10, 
                                    top_10=top_10,
                                    recent_ops=recent_ops,
                                    most_active_users=most_active_users,
                                    plusplus_count=plusplus_count,
                                    minusminus_count=minusminus_count,
                                    target_count=target_count,
                                    user_count=user_count),
      paths.LANDING_PAGE_NAME)
  
  # Generating main feed
  templates.Write(
      templates.ActivityFeedTemplate(title="Recent activity",
                                     path=paths.MAIN_FEED_NAME,
                                     html_path=paths.LANDING_PAGE_NAME,
                                     ops=recent_ops,
                                     display_op_count=20),
      paths.MAIN_FEED_NAME)

  # Update all the targets that were affected
  Debug("Generating %d target pages" % len(update_set.targets))
  for target in update_set.targets:
    score = scores_by_target[target]

    (plusplus_count, minusminus_count, target_count, user_count) = \
        GetScoresCounts([score])
    
    counterpart_user = api.GetUser(target, always_cache=True)
    counterpart_user_is_here = \
        counterpart_user and counterpart_user.id in scores_by_user_id_and_target

    templates.Write(
      templates.TargetPageTemplate(
          target=target,
          score=score,
          counterpart_user=counterpart_user,
          counterpart_user_is_here =counterpart_user_is_here,
          plusplus_count=plusplus_count,
          minusminus_count=minusminus_count,
          user_count=user_count),
      paths.GetTargetOutputPath(target))

    templates.Write(
        templates.ActivityFeedTemplate(
            title="Recent activity for %s" % target,
            path=paths.GetTargetFeedOutputPath(target),
            html_path=paths.GetTargetOutputPath(target),
            ops=score.recent_ops),
        paths.GetTargetFeedOutputPath(target))


  # All the users that created ops
  Debug("Generating %d user pages" % len(update_set.user_ids))
  for user_id in update_set.user_ids:
    scores = scores_by_user_id_and_target[user_id].values()
    user_recent_ops = recent_ops_by_user_id[user_id]
    user = scores[0].ops[0].message.user
    
    (bottom_10, top_10) = GetScoresTops(scores)
    (plusplus_count, minusminus_count, target_count, user_count) = \
        GetScoresCounts(scores)

    counterpart_score = scores_by_target.get(user.screen_name, None)

    friends = api.GetFriends(user)    

    friends_scores = GetScoresWithFriends(user, friends)
    (friends_bottom_10, friends_top_10) = GetScoresTops(
        friends_scores.values())
    (friends_plusplus_count, friends_minusminus_count, 
     friends_target_count, friends_user_count) = \
        GetScoresCounts(friends_scores.values())
    
    friends_recent_ops = []
    for score in friends_scores.values():
      for op in score.ops:
        AddOpToRecentOps(op, 
                         friends_recent_ops,
                         op_count=LANDING_PAGE_RECENT_OP_COUNT)
    
    templates.Write(
      templates.UserPageTemplate(
          user=user,
          counterpart_score=counterpart_score,
      
          bottom_10=bottom_10,
          top_10=top_10,
          recent_ops=user_recent_ops,
 
          plusplus_count=plusplus_count,
          minusminus_count=minusminus_count,
          target_count=target_count,
         
          friends=friends,
          friends_bottom_10=friends_bottom_10,
          friends_top_10=friends_top_10,
          friends_recent_ops=friends_recent_ops,
          
          friends_plusplus_count=friends_plusplus_count,
          friends_minusminus_count=friends_minusminus_count,
          friends_target_count=friends_target_count),
      paths.GetUserOutputPath(user))

    templates.Write(
        templates.ActivityFeedTemplate(
            title="Recent activity by %s" % user.screen_name,
            path=paths.GetUserFeedOutputPath(user),
            html_path=paths.GetUserOutputPath(user),
            ops=user_recent_ops),
        paths.GetUserFeedOutputPath(user))

    templates.Write(
        templates.ActivityFeedTemplate(
            title="Recent activity by %s's clique" % user.screen_name,
            path=paths.GetUserCliqueFeedOutputPath(user),
            html_path=paths.GetUserOutputPath(user),
            ops=friends_recent_ops,
            display_op_count=20),
        paths.GetUserCliqueFeedOutputPath(user))


  DebugPop()

def GetCheckpoint(log_name, previous_ops):
  path = paths.GetCheckpointPath(log_name)
  
  if os.path.exists(path):
    file = open(path, "r")
    checkpoint = int(file.read())
    file.close()
    return checkpoint
  elif previous_ops:
    return previous_ops[-1].message.created_at_in_seconds
  else:
    return None

def UpdateCheckpoint(log_name, messages):
  if len(messages):
  
    messages.sort(
        lambda a, b: int(a.created_at_in_seconds - b.created_at_in_seconds))
    
    last_message = messages[-1]
    
    file = open(paths.GetCheckpointPath(log_name), "w")
    file.write(str(last_message.created_at_in_seconds))
    file.close()
    
    return last_message.created_at_in_seconds
  else:
    return None

def main(argv):
  opts, args = getopt.getopt(argv, "", [
    "username=",
    "password=",

    "no_upload", 
    "run_once",
    "no_twitter_fetch",
    "no_rebuild",
    "no_log_restore",
    "no_ack",
  ])
  
  opts_map = {}
  for (name, value) in opts:
    opts_map[name[2:]] = value
  
  no_upload = "no_upload" in opts_map
  run_once = "run_once" in opts_map
  no_twitter_fetch = "no_twitter_fetch" in opts_map
  no_rebuild = "no_rebuild" in opts_map
  no_log_restore = "no_log_restore" in opts_map
  no_ack = "no_ack" in opts_map
  
  username = opts_map["username"]
  password = opts_map["password"]
  
  api.Init(
      username=username,
      password=password,
      friends_filter=lambda friend: friend.id in scores_by_user_id_and_target,
  )
  
  # Twitter API requests will ocasionally hang forever
  socket.setdefaulttimeout(15)
  
  DebugPush()
  Debug("Loading logs...")
  DebugPush()
  if not no_log_restore:
    direct_ops = GetOpsFromLog(DIRECT_LOG_NAME)
    friends_ops = GetOpsFromLog(FRIENDS_LOG_NAME)
  else:
    direct_ops = []
    friends_ops = []
  DebugPop()
  
  Debug("Processing restored ops...")
  DebugPush()
  update_set = updateset.UpdateSet()
  ProcessOps(direct_ops, update_set)
  ProcessOps(friends_ops, update_set)
  Debug("Done")
  DebugPop()
  
  # Keep refreshing both
  direct_checkpoint = GetCheckpoint(DIRECT_LOG_NAME, direct_ops)
  friends_checkpoint = GetCheckpoint(FRIENDS_LOG_NAME, friends_ops)
  
  # If this flag is given, then we don't have to regenerate all pages for ops
  # that we restored from logs, since it's assumed that there have been no
  # template changes. This is useful when restarting the script immediately
  # after a failure
  if no_rebuild:
    update_set = updateset.UpdateSet()
  
  iteration_count = 0
  
  while True:
  
    DebugSeparator()
  
    iteration_start = time.time()
    Debug("Iteration %d" % iteration_count)
    DebugPush()
  
    new_ops = []
  
    if not no_twitter_fetch:
      Debug("Fetching new messages...")
      DebugPush()
      
      new_direct_messages = api.GetDirectMessages(direct_checkpoint)
      Debug("Got %d new direct messages" % len(new_direct_messages))
      if new_direct_messages:
        new_direct_ops = ExtractOps(new_direct_messages, True)
        LogOps(new_direct_ops, DIRECT_LOG_NAME)
        ProcessOps(new_direct_ops, update_set)
        
        new_ops.extend(new_direct_ops)
        direct_ops.extend(new_direct_ops)
        direct_ops.sort(Op.TimeCompare)
    
        direct_checkpoint = UpdateCheckpoint(DIRECT_LOG_NAME, new_direct_messages)

      # Twitter seems to ocasionally deliver messages out of order, and by using
      # the since parameter we will miss them. Therefore once in a while we do
      # a full fetch to catch these (we ignore messages we've already 
      # processed)
      full_fetch = (iteration_count % 10) == 9      
      
      new_friends_messages = api.GetFriendsTimeline(
          since_seconds=not full_fetch and friends_checkpoint or None)
      Debug("Got %d new friends messages" % len(new_friends_messages))
      if new_friends_messages:
        new_friends_ops = ExtractOps(new_friends_messages, False)
        LogOps(new_friends_ops, FRIENDS_LOG_NAME)
        ProcessOps(new_friends_ops, update_set)
    
        new_ops.extend(new_friends_ops)
        friends_ops.extend(new_friends_ops)
        friends_ops.sort(Op.TimeCompare)
    
        friends_checkpoint = UpdateCheckpoint(FRIENDS_LOG_NAME, 
                                              new_friends_messages)
    
      DebugPop()
    
    # Generate output
    if not update_set.IsEmpty():
      Debug("Updating output...")
      UpdateOutput(update_set)
      
      if not no_upload:
        Debug("Uploading output...")
        templates.UploadOutput()

    # Acknowledge ops (done after output has been generated and uploaded, since
    # the website needs to refresh as quickly as posible)
    if new_ops and not no_ack:
      AcknowledgeOps(api, new_ops)
  
    # Reset update_set for next iteration (we don't reset it at the start of the
    # loop, since we generate some updates (by loading all data) before the loop
    # starts and we want to include those in the first update set)
    update_set = updateset.UpdateSet()
    
    Debug("Done, fetched %d URLs" % api.GetUrlFetchCount())
    api.ResetUrlFetchCount()
    
    if run_once:
      break
  
    # We're restricted to 70 requests per hour, and each iteration is two 
    # requests, thus we want 2 minutes between iterations
    iteration_end = time.time()
    sleep_time = 120 - (iteration_end - iteration_start)
    if sleep_time > 0:
      Debug("Sleeping for %5.2f seconds..." % sleep_time)
      time.sleep(sleep_time)
    
    DebugPop()

    iteration_count += 1
  
  DebugPop()

if __name__ == "__main__":
    main(sys.argv[1:])