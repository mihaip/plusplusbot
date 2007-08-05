import os
import urllib

BASE_PATH = "/Users/mihai/Vulcan/Projects/plusplusbot"
LOG_PATH = os.path.join(BASE_PATH, "logs")
OUTPUT_PATH = os.path.join(BASE_PATH, "out")

LANDING_PAGE_NAME = "index.html"
MAIN_FEED_NAME = "index.xml"

def GetLogPath(log_name):
  return os.path.join(LOG_PATH, log_name)
  
def GetCheckpointPath(log_name):
  return os.path.join(LOG_PATH, log_name + ".since")

def GetOutputPath(file_name):
  return os.path.join(OUTPUT_PATH, file_name)

def GetRemotePath(local_relative_path):
  return os.path.join("public_html/ppb", local_relative_path);

def GetTargetOutputPath(target, url_quote=False):
  if url_quote:
    target = unicode(target).encode("utf-8")
    target = urllib.quote(target)
  return os.path.join("targets", target)

def GetTargetFeedOutputPath(target, url_quote=False):
  if url_quote:
    target = unicode(target).encode("utf-8")
    target = urllib.quote(target)
  return os.path.join("targets", target) + ".xml"

def GetUserOutputPath(user):
  return os.path.join("users", user.screen_name)

def GetUserFeedOutputPath(user):
  return os.path.join("users", user.screen_name) + ".xml"

def GetUserCliqueFeedOutputPath(user):
  return os.path.join("users", user.screen_name) + "_clique.xml"
  

def GetPartychatPath():
  return os.path.join(BASE_PATH, "ppblog");