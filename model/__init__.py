from google.appengine.ext import db

from user import User
from tag import Tag, TagJoin
from map import Map, Comment, Vote, Favorite, InvalidMapError
from sequence import Sequence


class SundayN(db.Model):
  number = db.IntegerProperty(required=True)
  text = db.TextProperty(required=True)


class News(db.Model):
  title = db.StringProperty(required=True)
  text = db.TextProperty(required=True)
  lastupdated = db.DateTimeProperty(required=True, auto_now=True)


class AdminLog(db.Model):
  is_admin = db.BooleanProperty(required=True, default=False)
  user = db.ReferenceProperty(User, required=True, collection_name="user")
  when = db.DateTimeProperty(required=True, auto_now_add=True)
  handler = db.StringProperty(required=True)
  url = db.StringProperty(required=True)
  action = db.StringProperty(required=True)
  message = db.TextProperty()
  ref = db.ReferenceProperty(db.Model)

  @staticmethod
  def create(handler, action=None, message=None, ref=None):
    if not action:
      action = handler.request.method
    log = AdminLog(
        is_admin=handler.user.isadmin,
        user=handler.user,
        handler=handler.__class__.__name__,
        url=handler.request.url,
        action=action,
        message=message,
        ref=ref)
    log.put()
    return log
