from google.appengine.ext import db
from google.appengine.api import urlfetch
import urllib
import datetime
import logging
import cgi
import random

import config
import model
import lib
from lib import imaginrequest

NUM_COMMENTS = 10
NUM_MAPS = 6

class UserInfoPage(lib.BaseHandler):
  def can_modify(self, user):
    return self.session.get("logged_in", False) and (self.user.key() == user.key()
                                                     or self.user.isadmin)
  
  def get(self, username=None, action=None):
    if username is None:
      if not self.session.get("logged_in", False):
        self.redirect("/login")
      else:
        self.redirect("/user/%s" % (urllib.quote(self.user.username), ))
      return
    
    username = urllib.unquote(urllib.unquote(username))
    if action is None or action == "edit":
      template_values = self.GetTemplateValues("get")
      user = model.User.get_by_username(username)
      template_values['username'] = username
      if not user:
        self.response.set_status(404)
        self.RenderTemplate("nosuchuser.html", template_values)
        return

      template_values['profile_user'] = user
      template_values['canmodify'] = self.can_modify(user)
      if user.disabled_until:
        template_values['disable_days'] = (user.disabled_until - datetime.datetime.now()).days

      attributes = []
      if user.isadmin:
        attributes.append("Administrator")
      elif user.ismoderator:
        attributes.append("Moderator")
      elif user.adfree:
        attributes.append("Donator")
      if user.canreview:
        attributes.append("Reviewer")
      if user.isdisabled:
        attributes.append("Disabled")
      template_values["attributes"] = ", ".join(attributes)
    
      if action=="edit" and self.can_modify(user):
        self.RenderTemplate("edituserinfo.html", template_values)
      else:
        if user.favourite_count > user.map_count and user.favourite_count > 0:
          # Show favourites
          q = model.Favorite.all()
          q.ancestor(user)
          q.order("-added")
          favs = q.fetch(NUM_MAPS)
          fav_maps = model.Map.get([x.map_key() for x in favs])
          fav_maps.reverse()
          template_values["favorites"] = fav_maps
        elif user.map_count > 0:
          q = model.Map.all()
          q.filter("user =", user)
          q.filter("unlisted =", False)
          q.order("-float_num")
          maps = q.fetch(NUM_MAPS)
          maps.reverse()
          template_values["maps"] = maps
        self.RenderTemplate("userinfo.html", template_values)

  def post(self, username, action=None):
    username = urllib.unquote(urllib.unquote(username))
    template_values = self.GetTemplateValues("post")
    user = model.User.get_by_username(username)
    template_values['username'] = username
    if not user:
      self.response.set_status(404)
      self.RenderTemplate("nosuchuser.html", template_values)
      return

    if self.can_modify(user):
      user.email = self.request.POST.get("email", user.email)
      user.profile = self.request.POST.get("profile", user.profile)
      avatar_img = self.request.POST.get("avatar_img", None)
      if isinstance(avatar_img, cgi.FieldStorage):
        avatar_path = "numa/avatars/%s" % (user.key().name())
        ir = imaginrequest.ImaginRequest()
        ir.add_image("src", avatar_img.filename, avatar_img.value)
        ir.op("convert", "src", "src", "RGBA")
        ir.op("thumbnail", "src", 64, 64)
        ir.op("s3send", "src", "PNG", config.s3_pubkey, config.s3_privkey, config.s3_bucket,
              avatar_path, "public-read")

        try:
          response = ir.execute()
          if response.status_code == 200:
            user.avatar = "http://static.notdot.net/%s?%d" % (avatar_path, random.randint(0, 65536))
          else:
            logging.error("Error uploading avatar: %s" % response.content)
            raise urlfetch.DownloadError()
        except urlfetch.DownloadError:
          self.RenderTemplate("internalerror.html", self.GetTemplateValues(None))
          return
      
      if self.user.isadmin:
        model.AdminLog.create(self, ref=user)
        user.canvote = bool(self.request.POST.get("canvote", False))
        user.canreview = bool(self.request.POST.get("canreview", False))
        user.validated = bool(self.request.POST.get("validated", False))
        user.ismoderator = bool(self.request.POST.get("ismoderator", False))
        user.isadmin = bool(self.request.POST.get("isadmin", False))
        user.adfree = bool(self.request.POST.get("adfree", False))
        user.title = self.request.POST.get("title", None)
        user.isdisabled = bool(self.request.POST.get("isdisabled", False))
        if user.isdisabled:
          user.disabled_why = self.request.POST.get("disabled_why", None)
          if self.request.POST.get("disabled_time"):
            user.disabled_until = (datetime.datetime.now() +
                                   datetime.timedelta(int(self.request.POST.get("disabled_time", 0))))
        else:
          user.disabled_why = None
          user.disabled_until = None
      user.put()

    self.redirect("/user/%s" % urllib.quote(user.username))


class AuthorActivityPage(lib.BaseHandler):
  AUTHORS_PER_PAGE = 10
  MAPS_PER_AUTHOR = 6
  
  def get(self):
    template_values = self.GetTemplateValues("get")
    authors = model.User.all().order("-last_submission").fetch(self.AUTHORS_PER_PAGE)
    entries = [(x, model.Map.all().filter("user =", x).filter("unlisted =", False).order("-float_num").fetch(self.MAPS_PER_AUTHOR)[::-1]) for x in authors]
    template_values["entries"] = entries
    self.RenderTemplate("authoractivity.html", template_values)

class WhosWhoPage(lib.BaseHandler):
  def get(self):
    template_values = self.GetTemplateValues("get")
    template_values['admins'] = model.User.all().filter("isadmin =", True).fetch(100)
    template_values['mods'] = [x for x in model.User.all().filter("ismoderator =", True).fetch(100) if not x.isadmin]
    template_values['reviewers'] = model.User.all().filter("canreview =", True).fetch(100)
    self.RenderTemplate("whoswho.html", template_values)
