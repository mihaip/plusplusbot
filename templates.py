import os

import calendar
import datetime
import subprocess
import time
import xml.sax.saxutils

import templet
import paths
from util import *

class PageTemplate(templet.UnicodeTemplate):
  template = r'''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
	<meta http-equiv="content-type" content="text/html; charset=utf-8">
  <title>plusplusbot$<subtitle_plaintext_template></title>
  <link rel="stylesheet" type="text/css" href="$<top_template>/main.css">
  <script type="text/javascript" src="$<top_template>/main.js"></script>
  <link href="$<top_template>/$<feed_path_template>"
        rel="alternate" 
        title="plusplusbot.com Atom Feed"
        type="application/atom+xml">
  <link href="$<top_template>/favicon.ico" rel="SHORTCUT ICON">
</head>
<body>
<div id="header">
  <h1><a href="$<top_template>/index.html">plusplusbot</a>$<subtitle_template></h1>
  <div id="timestamp">
    Last updated ${{self.relative_timestamp_template(timestamp=calendar.timegm(time.gmtime()))}}
  </div>
  <div id="feedback">
    <script type="text/javascript">printEmail("Feedback");</script>
  </div>
</div>
$<body_template>

<div id="footer">
a <a href="http://persistent.info/">persistent.info</a> production.
&copy; 2007 Mihai Parparita
</div>
</body>
</html>
  '''
  
  relative_timestamp_template = r'''
  <script type="text/javascript">writeRelativeTimestamp($timestamp);</script>
'''

  target_link_template = r'''
${{
  anchor_text=vars().get('anchor_text', target)
}}
    <a class="target" href="$<top_template>/${paths.GetTargetOutputPath(target, url_quote=True)}">$anchor_text</a>'''

  user_link_template = r'''
${{
  icon_size=vars().get('icon_size', 14)
  anchor_text=vars().get('anchor_text', user.screen_name)
}}

${{
  if icon_size:
    self.user_icon_template(user=user,icon_size=icon_size)
}}
   <a class="user" href="$<top_template>/${paths.GetUserOutputPath(user)} "title="${user.name}">$anchor_text</a>'''

  user_icon_template = r'''
${{
  icon_size=vars().get('icon_size', 14)
}}
    <a class="user-image" 
       href="$<top_template>/${paths.GetUserOutputPath(user)}"
       title="${user.name}">
      <img src="${user.profile_mini_image_url}" width="$icon_size" height="$icon_size">
   </a>
'''

  anonymous_template = r'''
    <span class="user-image">
      <img src="anonymous.gif" width="14" height="14">
    </span>
    <span class="user">Anonymous</span>
'''

  sign_template = r'''
<span class="sign delta${delta}">${delta != 1 and '--' or '++'}</span>
'''
  
  feed_link_template = r'''
  <a href="$<top_template>/$feed_path" class="feed-link">
    <img src="$<top_template>/feed-icon.png" 
         width="14" 
         height="14"
         alt="Feed icon">
  </a>
'''

  score_table_template = r'''
<table class="scores data-table">
<caption>$title</caption>
<thead>
  <tr>
    <th>Score</th>
    <th>Target</th>
  </tr>
</thead>
<tbody>
  ${{
    if scores:
      for score in scores:
        self.score_row_template(score=score)
    elif "empty_message" in vars():
      self.score_table_empty_template(empty_message=empty_message)
  }}
</tbody>
</table>
'''

  score_table_empty_template = r'''
  <tr>
    <td colspan="2" class="empty">
      $empty_message
    </td>
  </tr>
'''
  
  score_row_template = r'''
<tr>
  <td class="score">${score.score}</td>
  <td class="target">
    ${{self.target_link_template(target=score.target)}}
  </td>
</tr>
'''
  
  op_table_template = r'''
${{
  hide_targets=vars().get('hide_targets', False)
  hide_users=vars().get('hide_users', False)
  feed_path=vars().get('feed_path', None)

  crowd_ops=vars().get('crowd_ops', False)
  display_op_count=vars().get('display_op_count', len(ops))
}}

<table class="op-table data-table">
  <caption>
    $title
    ${{
      if feed_path:
        self.feed_link_template(feed_path=feed_path)
    }}
  </caption>
  <thead>
    <tr>
      ${hide_targets and ' ' or '<th>Target</th>'}
      <th>Operation</th>
      <th>Sign, User and Reason</th>
    </tr>
  </thead>
  <tbody>
    ${{
      current_dupe_run = []
      visible_row_count = 0
      
      for i in range(0, len(ops)):
        if visible_row_count >= display_op_count: break
        
        op = ops[i]
        
        same_as_previous = False
        if crowd_ops and i > 0:
          same_as_previous = ops[i].Equals(ops[i - 1])
          
          if same_as_previous:
            current_dupe_run.append(i)
          else:
            visible_row_count += 1
            if current_dupe_run:
              if len(current_dupe_run) > 1:
                self.op_row_crowd_template(dupe_run=current_dupe_run)
              current_dupe_run = []

        self.op_row_template(
            op=op,
            hide_target=hide_targets,
            hide_user=hide_users,
            is_dupe=same_as_previous and len(current_dupe_run) > 1)
    }}
  </tbody>
</table>
'''

  op_row_crowd_template = r'''
<tr class="crowd">
  <td>&nbsp;</td>
  <td>
    <span class="link" 
          onclick="showDupes(this, [${",".join([str(id) for id in dupe_run[1:]])}])">...and ${len(dupe_run) - 1} more
    </span>
  </td>
</tr>
'''

  op_row_template = r'''
<tr class="${is_dupe and "dupe" or ""} ${op.is_anonymous and "anonymous" or ""}">
  ${{
    if not hide_target:
      if not hide_user:
        self.write('<td class="target"><div class="container">')
      else:
        self.write('<td><div class="container">')
        self.sign_template(delta=op.delta)
        self.write("'ed ")
        
      self.target_link_template(target=op.target)
      
      if not hide_user:
        self.write('</div></td>')
  }}

  ${{
    if not hide_user:
      self.write('<td class="sign-user-reason"><div class="container">')
      self.sign_template(delta=op.delta)
      self.write("'ed ")
      
      self.write('by ')
      if op.is_anonymous:
        self.anonymous_template()
      else:
        self.user_link_template(user=op.message.user)
  }}

  ${{
    if op.reason:
      self.write("(")
      self.write(Linkify(op.reason))
      self.write(")")
  }}

  ${{
    if not op.is_direct:
      self.write('<a href="%s" class="date">' % op.message_url)
    else:
      self.write('<span class="date">')

    self.relative_timestamp_template(timestamp=op.timestamp)

    if not op.is_direct:
      self.write('</a>')
    else:
      self.write('</span>')

  }}
  
  ${{
    if not op.is_anonymous:
      self.op_context_template(op=op)
  }}

  </div></td>
</tr>
'''

  op_context_template = r'''
  <div class="context">
    <div class="corner"></div>
    <strong>Tweet:</strong>
    ${op.message.text}
  </div>
'''
  
  user_list_template = r'''
<div class="user-list data-list">
  <div class="caption">$title</div>
  <ul>
    ${{
      for score in scores:
        self.user_list_item_template(score=score)
    }}
  </ul>
</div>
'''

  user_list_item_template = r'''
<li>
  ${{self.user_link_template(user=score.ops[0].message.user)}}
  (${score.increment_count} ${{self.sign_template(delta=1)}}'s
  and
  ${score.decrement_count} ${{self.sign_template(delta=-1)}}'s)
</li>
'''
  
  feed_path_template = ''
  
class LandingPageTemplate(PageTemplate):
  body_template = r'''
<table class="columns" id="intro-table">
  <tr>
    <td class="column left-column">
      <h2>Karma for anything and anyone</h2>
      
      <p>
        Did someone go out of their way to help you? Is a web site being 
        particularly slow and flaky? Make your feelings known with plusplusbot.
        You can ${{self.sign_template(delta=1)}} (pronounced "plusplus") or
        ${{self.sign_template(delta=-1)}} ("minusminus") anything. Think 
        brownie points (but archived forever).
      </p>
      <p>
        <script type="text/javascript">printEmail("Feedback");</script><noscript>Feedback</noscript> is welcome.
      </p>      
    </td>
    <td class="column right-column">
      <h2>Getting started</h2>
      <ol>
        <li>
          Make sure you have a <a href="http://twitter.com/">Twitter</a> 
          account.
        </li>
        <li>
          Add <a href="http://twitter.com/plusplusbot/">plusplusbot</a> as a 
          friend.
        </li>
        <li>
          To increment "foo", your most favorite thing in the world, send an 
          update with a message like:
          
          <p><b>foo++ because yadda yadda</b></p>
          
          <p>Within a minute, you'll get a confirmation message with foo's
          current score, and the website will update itself.</p>
          
          You can also use the form below or
          <a href="http://twitter.com/direct_messages/create/5406832"
          >send a direct message</a> to plusplusbot to avoid spamming your
          friends. Begin your direct message with a "!" to be anonymous (you
          coward!).
        </li>
      </ol>
    </td>
  </tr>
</table>

<form method="POST" id="send-form" action="http://twitter.com/direct_messages/create/5406832" onsubmit="return sendFormFillMessage();">
  <h3>Send a message now
    <div class="explanation">You must be signed in to Twitter and have plusplusbot listed as a friend. Messages may take a couple of minutes to be processed.</div>
  </h3>
  
  <table>
    <tr>
      <td><input id="send-target" size="20"></td>
      <td><img src="plusplusbutton.gif" id="send-plusplus" width="27" height="17" alt="plusplus" title="plusplus" onclick="sendFormSelect('plusplus')")></td>
      <td id="minusminus-cell"><img src="minusminusbutton.gif" id="send-minusminus" width="27" height="17" alt="minusminus" title="minusminus" onclick="sendFormSelect('minusminus')"></td>
      <td><input id="send-reason" size="40"></td>
      <td><input type="submit" value="Send" name="commit" id="submit"></td>
    </tr>
    <tr id="send-labels">
      <td>target</td>
      <td>&nbsp;</td>
      <td>&nbsp;</td>
      <td>reason (optional)</td>
      <td>&nbsp;</td>
    </tr>
  </table>
  <input type="hidden" name="text" id="send-text">
</form>

<div class="sentence">
  So far, there have been
  <span class="number">$plusplus_count</span> ${{self.sign_template(delta=1)}}'s
  and
  <span class="number">$minusminus_count</span> ${{self.sign_template(delta=-1)}}'s
  about
  <span class="number">$target_count</span> things
  by
  <span class="number">$user_count</span> people.
</div>

<table class="columns" id="home-columns">
  <tr>
    <td class="column" colspan="4">
      ${{self.op_table_template(ops=recent_ops,
                                title="Recent Activity",
                                feed_path=paths.MAIN_FEED_NAME,
                                crowd_ops=True,
                                display_op_count=20)}} 
    </td>
  </tr>

  <tr>
    <td class="column score-table-column">
      ${{self.score_table_template(scores=bottom_10,
                                   title="Least Liked")}}
    </td>
    <td class="column score-table-column">
      ${{self.score_table_template(scores=top_10,
                                   title="Most Adored")}}
    </td>
    <td class="column score-table-column" id="most-active-users-column">
      ${{self.user_list_template(scores=most_active_users, 
                                 title="Biggest Users")}}
    
    </td>
    <td class="column">&nbsp;</td>
  </tr>
</table>
'''
  
  top_template = '.'
  
  subtitle_plaintext_template = ''
  
  subtitle_template = ''
  
  feed_path_template = paths.MAIN_FEED_NAME

class TargetPageTemplate(PageTemplate):
  counterpart_user_template = r'''(who is also a user
    on <a href="http://twitter.com/${user.screen_name}">Twitter</a>${{
      if is_here: 
        self.write(" and ")
        self.user_link_template(user=user,
                                icon_size=None,
                                anchor_text='here')
    }})'''

  body_template = r'''
<div class="sentence">
"$target" ${{
  if counterpart_user:
    self.counterpart_user_template(target=target,
                                   user=counterpart_user,
                                   is_here=counterpart_user_is_here)
}} has been
${{self.sign_template(delta=1)}}'ed <span class="number">$plusplus_count</span> times
and
${{self.sign_template(delta=-1)}}'ed <span class="number">$minusminus_count</span> times
by a total of <span class="number">$user_count</span> people.
</div>

<table class="columns">
  <tr>
    <td class="column">
      ${{self.op_table_template(
             ops=score.display_ops, 
             title="Activity",
             hide_targets=True,
             feed_path=paths.GetTargetFeedOutputPath(target, url_quote=True))}}
    </td>
    <td class="column">
      ${{
        # No pointin listing top boosters if there hasn't been much activity,
        # since it'll just be a repetition of the activity list
        if len(score.display_ops) >= 5:
          boosters = score.GetTopUsers(False)
          
          # Only display top boosters if at least one isn't all negative
          # user has never plusplus'ed)
          all_negative = boosters[0].score < 0
          if not all_negative:
            self.user_list_template(scores=boosters, 
                                    title="Top Boosters")
  
          # No point in listing the detractors if there are less than 10 users
          # to begin with, they'll just be the same users as the boosters but
          # in reverse order
          if all_negative or len(boosters) == 10:
            self.user_list_template(scores=score.GetTopUsers(True), 
                                    title="Top Detractors")
      }}
    </td>
  </tr>
</table>
'''
  
  top_template = '..'
  
  subtitle_plaintext_template = r'''
  : $target 
  [${score.score > 0 and '+' or ''}${score.score}]
'''
  
  subtitle_template = r'''
  : $target 
  ${{
    if score.score > 0:
      self.write('<span class="score score-positive">+')
    elif score.score < 0:
      self.write('<span class="score score-negative">') 
    else:
      self.write('<span class="score score-zero">')
    
    self.write(score.score)
    
    self.write('</span>')
  }}
'''

  feed_path_template = '${paths.GetTargetFeedOutputPath(target, url_quote=True)}'

class UserPageTemplate(PageTemplate):
  counterpart_score_template = r'''(who is ${{
    self.target_link_template(
        target=score.target,
        anchor_text='at %s%d' % (score.score > 0 and '+' or ' ', score.score))
  }})'''

  body_template = r'''
<div class="sentence">
${user.screen_name} ${{
  if counterpart_score:
    self.counterpart_score_template(score=counterpart_score)
}} has 
${{self.sign_template(delta=1)}}'ed <span class="number">$plusplus_count</span> times
and
${{self.sign_template(delta=-1)}}'ed <span class="number">$minusminus_count</span> times
about <span class="number">$target_count</span> things.
</div>  

<table class="columns">
  <tr>
    <td class="column" rowspan="2">
      ${{self.op_table_template(ops=recent_ops,
                                title="Recent Activity",
                                hide_users=True,
                                feed_path=paths.GetUserFeedOutputPath(user))}}     
    </td>    
    <td class="column">
      ${{self.score_table_template(
          scores=bottom_10,
          title="Pet Peeves",
          empty_message="Nothing yet, they must not be bitter enough.")}}
    </td>
  </tr>
  <tr>
    <td class="column">
      ${{self.score_table_template(
          scores=top_10,
          title="Favorites",
          empty_message="Nothing yet, they must be too bitter.")}}
    </td>
  </tr>
</table>

${{
  if friends:
    self.with_friends_template(vars())
}}
'''

  with_friends_template = '''
<div id="friends-header">
  <h2>clique mode</h2>
  
  <div class="sentence">
    ${user.screen_name} and their
    <span class="number">${len(friends)}</span>
    <a href="http://twitter.com/${user.screen_name}/friends">friends</a>
    (${{
      for friend in friends:
        self.user_link_template(user=friend,icon_size=24)
    }})
    have
    ${{self.sign_template(delta=1)}}'ed 
    <span class="number">$friends_plusplus_count</span> times
    and
    ${{self.sign_template(delta=-1)}}'ed 
    <span class="number">$friends_minusminus_count</span> times
    about <span class="number">$friends_target_count</span> things.

    <div class="explanation">
      Only plusplusbot.com-using friends are counted.
    </div>
  </div>
</div>

<table class="columns">
  <tr>
    <td class="column" rowspan="2">
      ${{self.op_table_template(
          ops=friends_recent_ops,
          title="Recent Activity",
          feed_path=paths.GetUserCliqueFeedOutputPath(user),
          crowd_ops=True,
          display_op_count=20)}}     
    </td>
    <td class="column">
      ${{self.score_table_template(
          scores=friends_bottom_10,
          title="Bottom 10",
          empty_message="Nothing yet, this group must be a happy bunch")}}
    </td>
  </tr>
  <tr>
    <td class="column">
      ${{self.score_table_template(
          scores=friends_top_10,
          title="Top 10",
          empty_message="Nothing yet, this group must be a bitter bunch")}}
    </td>
</table>
'''

  top_template = '..'  
  
  subtitle_plaintext_template = ': ${user.screen_name}'
  
  subtitle_template = r''':
  <a href="http://twitter.com/${user.screen_name}">
  <img src="${user.profile_image_url}" width="48" height="48">
  ${user.screen_name}
  </a>
'''

  feed_path_template = '${paths.GetUserFeedOutputPath(user)}'


class ActivityFeedTemplate(PageTemplate):
  _in_escape = False
  
  def BeginEscape(self):
    assert not self._in_escape
    self._in_escape = True

    self._inner_out = self.out
    self.out = ActivityFeedTemplate.EscapedList(self._inner_out)
   
  def EndEscape(self):
    assert self._in_escape
    self._in_escape = False
    
    self.out = self._inner_out

  class EscapedList(object):
    def __init__(self, inner_list):
      self._inner_list = inner_list
    
    def append(self, i):
      self._inner_list.append(xml.sax.saxutils.escape(i))
    
    def extend(self, iterable):
      for i in iterable:
        self.append(i)
  
  template = r'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>tag:plusplusbot.com,2007:$path</id>
  <link rel="self" href="http://plusplusbot.com/$path"/>
  <link rel="alternate" type="text/html" href="http://plusplusbot.com/$html_path"/>
  <title>plusplusbot: $title</title>
  <updated>${datetime.datetime.utcnow().isoformat()}Z</updated>
  ${{
    display_op_count=vars().get('display_op_count', len(ops))
    display_op_count=min(display_op_count, len(ops))

    for i in range(0, display_op_count):
      self.op_entry_template(path=path,op=ops[i])
  }}
</feed>
'''
  op_entry_template = r'''
<entry>
  <id>tag:plusplusbot.com,2007:$path#${op.id}</id>
  <title type="text">
    ${{self.BeginEscape()}}
      ${op.is_anonymous and 'Anonymous' or op.message.user.screen_name}
      ${op.delta != 1 and '--' or '++'}'ed
      ${op.target}
    ${{self.EndEscape()}}
  </title>
  <updated>${op.message.created_at_datetime.isoformat()}Z</updated>
  <link rel="alternate" type="text/html" 
        href="$<top_template>/${paths.GetTargetOutputPath(op.target, url_quote=True)}"/>
  <content type="html">
    ${{self.BeginEscape()}}

      ${{
        if op.is_anonymous:
          self.anonymous_template()          
        else:
          self.user_link_template(user=op.message.user)
      }}
      ${{self.sign_template(delta=op.delta)}}'ed
      ${{self.target_link_template(target=op.target)}}

      ${{
        if op.reason:
          self.write("(")
          self.write(Linkify(op.reason))
          self.write(")")
      }}
    ${{self.EndEscape()}}
  </content>
  <author>
    <name>
      ${{self.BeginEscape()}}
        ${op.message.user.screen_name}
      ${{self.EndEscape()}}
    </name>
  </author>
</entry>
'''
  
  top_template = 'http://plusplusbot.com'

_write_log = []

def ResetWriteLog():
  del _write_log[:]

def Write(template, file_name):
  path = paths.GetOutputPath(file_name)
  _write_log.append(path)

  file = open(path, "w")
  
  file.write(str(template))
  
  file.close()
  
def GetTopLevelFiles(upload_files, dir_name, file_names):
  for file_name in file_names:
    file_path = os.path.join(dir_name, file_name)
    
    if not os.path.isdir(file_path) and file_path not in upload_files:
      upload_files.append(file_path)

  # Don't want to recurse, scp does that already
  del file_names[:]

def UploadFiles(dir, files):
  Debug("Uploading %d files in '%s'" % (len(files), dir))

  relative_dir_path = dir[len(paths.OUTPUT_PATH) + 1:]
  remote_dir_path = paths.GetRemotePath(relative_dir_path)
  
  args = [
    "scp", 
    "-p", # preserve timestamps
    "-q" # quiet
  ]
  
  for file in files:
    args.append(os.path.join(dir, file))
  
  args.append("mihai@mscape.com:%s" % remote_dir_path)
  
  subprocess.call(args)

def UploadOutput():
  upload_files = _write_log
  
  # Gather other top-level files, since they may change at any point
  # TODO(mihaip): check mod dates and/or only do this every N times
  os.path.walk(paths.OUTPUT_PATH, GetTopLevelFiles, upload_files)
  
  # Group files by directory, so that those can be uploaded at once
  files_by_dir = {}
  
  for path in upload_files:
    dir = os.path.dirname(path)
    if dir not in files_by_dir:
      files_by_dir[dir] = []
    files_by_dir[dir].append(os.path.basename(path))

  DebugPush()
  for dir in files_by_dir:
    files = files_by_dir[dir]
    UploadFiles(dir, files)
  DebugPop()