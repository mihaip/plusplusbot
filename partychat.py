def AppendPartychatOps(ops):
  PARTYCHAT_TO_TWITTER_MAP = {
    'dolapo@gmail.com': twitter.User(id=28163, screen_name='dolapo'),
    'kushaldave@gmail.com': twitter.User(id=696333, screen_name='krave'),
    'ak@q00p.net': twitter.User(id=774300, screen_name='ak'),
    'mihai.parparita@gmail.com': twitter.User(id=28203, screen_name='mihai'),
    'mishmosh@gmail.com': twitter.User(id=10644, screen_name='mishmosh'),
    'dtbentley@gmail.com': twitter.User(id=1050431, screen_name='dbentley'),
    'nsanch@gmail.com': twitter.User(id=852041, screen_name='nsanch')
  }
  
  ROBOT_FRIEND_USER = twitter.User(id=5634412, screen_name='robot_friend')
  
  # Begin fake timestamps on 1/1/2007 at midnight
  TIMESTAMP_BASELINE = 1167609600
  # space out fake timestamps by 2 hours and 3 minutes
  TIMESTAMP_INCREMENT = (2 * 60 + 3) * 60

  ppblog_file = open(paths.GetPartychatPath())
  reader = csv.reader(ppblog_file, delimiter='\t')
  
  id_counter = 0
  
  for (user, room, target, reason, sign) in reader:
    if room != 'pancake-ny': continue
    
    user = PARTYCHAT_TO_TWITTER_MAP.get(user, ROBOT_FRIEND_USER)
    
    fake_timestamp = TIMESTAMP_BASELINE + TIMESTAMP_INCREMENT * id_counter
    created_at = time.strftime('%a %b %d %H:%M:%S +0000 %Y', 
                               time.localtime(fake_timestamp))
    
    message = twitter.Status(created_at=created_at,
                             id=id_counter,
                             text=target + sign + sign + " " + reason,
                             user=user)
    
    if sign == "+":
      delta = 1
    else:
      delta = -1
    
    op = Op(target=target,
            delta=delta,
            reason=reason,
            message=message,
            is_anonymous=False,
            is_direct=True)
    
    ops.append(op)
    
    id_counter += 1
  
  ppblog_file.close()

  ops.sort(Op.TimeCompare)