from google.appengine.ext import db
from google.appengine.api import urlfetch
import datetime

import model
import lib

class HomePage(lib.BaseHandler):
  def AddFeaturedTag(self, map_key):
    map = model.Map.get(map_key)
    if "featured" in map.tags: return False
    map.tags.add(u"featured")
    map.put()
    return True

  def IncrementFeaturedCount(self, user_key):
    user = model.User.get(user_key)
    user.featured_map_count += 1
    user.put()
  
  def get(self, request, page=""):
    template_values = self.GetTemplateValues("get")
    if page == "news.atom":
      return self.RenderTemplate("news.atom", template_values)
    else:
      featured = model.Map.all()
      today = datetime.datetime.today()
      featured.filter("featured_date >", None)
      featured.filter("featured_date <=", today)
      featured.order("-featured_date")
      featured_map = featured.get()
      if featured_map and featured_map.featured_date:
        if "featured" not in featured_map.tags:
          added = db.RunInTransaction(self.AddFeaturedTag, featured_map.key())
          if added:
            tag = model.Tag.get_or_insert_tag("featured")
            tag.count += 1
            tag.put()
            db.RunInTransaction(self.IncrementFeaturedCount, featured_map.user.key())
        if self.session.get("logged_in", False):
          template_values["faved"] = model.Favorite.Exists(self.user.key(), featured_map.key())
        template_values["featured"] = featured_map
      
      return self.RenderTemplate("index.html", template_values)
      
  def GetTemplateValues(self, method):
    template_values = super(HomePage, self).GetTemplateValues(method)
    newsitems = model.News.all().order("-lastupdated")
    template_values["newsitems"] = newsitems.fetch(10)

    return template_values
