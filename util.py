import codecs
import csv
import cStringIO
import re
import sys
import time

_debug_time_stack = []

def Debug(message):
  prefix = "  " * (len(_debug_time_stack) - 1)
  start_time = _debug_time_stack[-1]
  current_time = time.time()
  timestamp = current_time - start_time
  print >> sys.stderr, "[%8.2f] %s%s" % (timestamp, prefix, message);
  
def DebugPush():
  _debug_time_stack.append(time.time())

def DebugPop():
  _debug_time_stack.pop()

def DebugSeparator():
  print >> sys.stderr, ""

URL_RE = re.compile("(http://.[^\s(),]+)")

def Linkify(str):
  return URL_RE.sub('<a rel="nofollow" href="\\1">\\1</a>', str)


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

class UnicodeDictReader:
  """
  A CSV reader which will iterate over lines in the CSV file "f",
  which is encoded in the given encoding.
  """

  def __init__(self, 
               csvfile,
               fieldnames=None,
               restkey=None,
               restval=None,
               dialect=csv.excel,
               encoding="utf-8",
               **kwds):
      csvfile = UTF8Recoder(csvfile, encoding)
      self.reader = csv.DictReader(csvfile,
                                   fieldnames=fieldnames,
                                   restkey=restkey,
                                   restval=restval,
                                   dialect=dialect,
                                   **kwds)

  def next(self):
      encoded_dict = self.reader.next()
      decoded_dict = {}
      for key in encoded_dict:
        value = encoded_dict[key]
        if value:
          decoded_dict[key] = unicode(value, "utf-8")
        else:
          decoded_dict[key] = value
      return decoded_dict

  def __iter__(self):
      return self
            
class UnicodeDictWriter:
  """
  A CSV writer which will write rows to CSV file "f",
  which is encoded in the given encoding.
  """
  
  def __init__(self, 
               csvfile,
               fieldnames,
               restval="",
               extrasaction='raise',
               dialect=csv.excel,
               encoding="utf-8",
               **kwds):
    # Redirect output to a queue
    self.queue = cStringIO.StringIO()
    self.writer = csv.DictWriter(self.queue, 
                                 fieldnames,
                                 restval=restval,
                                 extrasaction=extrasaction,
                                 dialect=dialect,
                                 **kwds)
    self.stream = csvfile
    self.encoder = codecs.getincrementalencoder(encoding)()
  
  def writerow(self, dict):
    encoded_dict = {}
    for key in dict.keys():
      value = unicode(dict[key])
      encoded_dict[key] = value.encode("utf-8")
    self.writer.writerow(encoded_dict)

    # Fetch UTF-8 output from the queue ...
    data = self.queue.getvalue()
    data = data.decode("utf-8")
    # ... and reencode it into the target encoding
    data = self.encoder.encode(data)
    # write to the target stream
    self.stream.write(data)
    # empty queue
    self.queue.truncate(0)
  
  def writerows(self, rows):
      for row in rows:
          self.writerow(row)
          