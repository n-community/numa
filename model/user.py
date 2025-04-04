from google.appengine.ext import db
import datetime
import hashlib
import hmac
import logging
import math
import random
from urllib.parse import urlencode

import config
from . import arrayproperty

CURVE_STEEPNESS = 0.10
GRAPH_WIDTH = 150
BELL_CURVE = [math.exp(-1*((x*CURVE_STEEPNESS)**2)) for x in range(GRAPH_WIDTH)]
CHART_CHAR_MAP = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

def asChartValues(hist):
  length = len(CHART_CHAR_MAP) - 1
  return "".join(CHART_CHAR_MAP[int(x*length)] for x in hist)

class User(db.Model):
  HISTOGRAM_SIZE = 10
  
  username = db.StringProperty(required=True)
  pass_hash = db.BlobProperty()
  email = db.StringProperty()
  title = db.TextProperty()
  avatar = db.StringProperty()

  ismoderator = db.BooleanProperty(required=True, default=False)
  isadmin = db.BooleanProperty(required=True, default=False)
  isdisabled = db.BooleanProperty(required=True, default=False)
  disabled_why = db.TextProperty()
  disabled_until = db.DateTimeProperty()
  validated = db.BooleanProperty(required=True, default=False)
  canvote = db.BooleanProperty(required=True, default=True)
  canreview = db.BooleanProperty(required=True, default=False)
  adfree = db.BooleanProperty(required=True, default=False)
  
  map_count = db.IntegerProperty(required=True, default=0)
  rated_map_count = db.IntegerProperty(required=True, default=0)
  featured_map_count = db.IntegerProperty(required=True, default=0)
  old_rating_histogram = db.ListProperty(int, name="rating_histogram")
  rating_histogram = arrayproperty.ArrayProperty(
      'i', default=[0]*HISTOGRAM_SIZE, name="new_rating_histogram")
  ratings = db.IntegerProperty(required=True, default=0)
  last_submission = db.DateTimeProperty(required=True,
                                        default=datetime.datetime.fromtimestamp(0))
  favourite_count = db.IntegerProperty(required=True, default=0)

  # Number of maps this user has with unread comments
  num_unread_maps = db.IntegerProperty(required=True, default=0)

  profile = db.TextProperty()

  @staticmethod
  def get_key_name(username):
    return "_"+hashlib.sha1(username.lower().encode()).hexdigest()

  @staticmethod
  def get_key(username):
    return db.Key.from_path("User", User.get_key_name(username))

  @staticmethod
  def new(username):
    user = User(key_name=User.get_key_name(username), username=username)
    user.avatar = "/static/avatars/Avatar%d.png" % random.randrange(1,7)
    return user

  @staticmethod
  def get_by_username(username):
    return User.get(User.get_key(username))

  @staticmethod
  def GetPasswordHash(username, password):
    h = hmac.new(
      config.hmac_secret.encode(),
      User.get_key_name(username).encode("utf-8"),
      hashlib.sha1
    )
    h.update(password.encode("utf-8"))
    return h.digest()
    
  def GetEmailHash(self):
    return hmac.new(
      config.hmac_secret.encode(),
      (u"validate|" + self.email).encode("utf-8"),
      hashlib.sha1
    ).hexdigest()

  def RecordNewMap(self, delta=1):
    def DoRecordNewMap():
      user = User.get(self.key())
      user.map_count += delta
      user.last_submission = datetime.datetime.utcnow()
      user.put()

    db.run_in_transaction(DoRecordNewMap)

  def GetRatingHistogram(self):
    maxval = 0
    hist = [0] * GRAPH_WIDTH
    for i in range(GRAPH_WIDTH):
      ipercent = float(i) / (GRAPH_WIDTH - 1)
      for j in range(len(self.rating_histogram)):
        jpercent = float(j) / (User.HISTOGRAM_SIZE - 1)
        pos = int(abs(ipercent - jpercent) * (GRAPH_WIDTH - 1))
        hist[i] += BELL_CURVE[pos] * self.rating_histogram[j]
      if hist[i] > maxval:
        maxval = hist[i]
    
    # Normalize
    if maxval > 0:
      for i in range(GRAPH_WIDTH):
        hist[i] = hist[i] / maxval
    
    return hist

  def GetRatingHistogramURL(self):
    params = {
      "cht": "ls", # Sparkline
      "chs": "150x50",
      "chco": "4d89f9", # Blue
      "chd": "s:%s" % asChartValues(self.GetRatingHistogram()),
      "chf": "bg,s,00000000", # Transparent background
      "chxt": "x", # X labels only
      "chxl": "0:|0|1|2|3|4|5", # Labels
      "chxs": "0,dbd7d0", # Label color
      "chm": "B,4d89f9,0,0,0", # Fill
      "chls": "1,1,0", # Line width 1
    }
    return "http://chart.apis.google.com/chart?%s" % urlencode(params)
