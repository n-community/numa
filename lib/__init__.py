from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext import db
import os
import logging

import model


webapp.template.register_template_library('lib.templatefilters')

class BaseHandler(webapp.RequestHandler):
  template_names = {}
  session = None
  
  def initialize(self, request, response):
    super(BaseHandler, self).initialize(request, response)
    self.session = self.request.environ['beaker.session']
    if 'user' in self.session:
      user_key = db.Key(self.session['user'])
      user_key = db.Key.from_path('User', user_key.id_or_name())
      self.user = model.User.get(user_key)
      logging.info("User: %s", self.user.username)
      if self.user.isdisabled:
        logging.info("Logging disabled user '%s' out." % self.user.username)
        del self.session['user']
        self.session['logged_in'] = False
        self.session.save()
    else:
      self.user = None
      
  def GetTemplatePath(self, template):
    return os.path.join(os.path.dirname(__file__), "..", "templates", template)

  def RenderTemplate(self, template_name, template_values):
    self.response.out.write(
        template.render(self.GetTemplatePath(template_name),
                               template_values))

  def GetTemplateValues(self, method):
    return {
      "session": self.session,
      "user": self.user,
	  "path_qs": self.request.path_qs,
	  "logged_in": self.session.get("logged_in", False)
    }

  def get(self):
    self.RenderTemplate(self.template_names["get"],
                        self.GetTemplateValues("get"))


def RequiresLogin(fun):
  def RequiresLoginDecorator(self, *args, **kwargs):
    if not self.session.get("logged_in", False):
      self.redirect("/login")
      return
    return fun(self, *args, **kwargs)
  return RequiresLoginDecorator

def RequiresModerator(fun):
  def RequiresModeratorDecorator(self, *args, **kwargs):
    if not self.session.get("logged_in", False):
      self.redirect("/login")
      return
    elif not self.user.ismoderator:
      self.response.set_status(403)
      self.RenderTemplate("permissiondenied.html", self.GetTemplateValues(None))
      return
    return fun(self, *args, **kwargs)
  return RequiresModeratorDecorator

def RequiresAdmin(fun):
  def RequiresAdminDecorator(self, *args, **kwargs):
    if not self.session.get("logged_in", False):
      self.redirect("/login")
      return
    elif not self.user.isadmin:
      self.response.set_status(403)
      self.RenderTemplate("permissiondenied.html", self.GetTemplateValues(None))
      return
    return fun(self, *args, **kwargs)
  return RequiresAdminDecorator

def nify_str(s):
  return s.replace("&", "").replace("$", "").replace("#", "")
