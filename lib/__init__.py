from google.appengine.ext import db
from django.views import View
from django.shortcuts import render, redirect

import os
import logging

import model

class BaseHandler(View):
  template_names = {}
  session = None

  def dispatch(self, request, *args, **kwargs):
    self.session = request.session
    if 'user' in self.session:
      user_key = db.Key(self.session['user'])
      user_key = db.Key.from_path('User', user_key.id_or_name())
      self.user = model.User.get(user_key)
      logging.info("User: %s", self.user.username)
      if self.user.isdisabled:
        logging.info("Logging disabled user '%s' out." % self.user.username)
        del self.session['user']
        self.session['logged_in'] = False
    else:
      self.user = None
    return super().dispatch(request, *args, **kwargs)

  def GetTemplateValues(self, method):
    return {
      "session": self.session,
      "user": self.user,
      "path_qs": self.request.get_full_path(),
      "logged_in": self.session.get("logged_in", False)
    }

  def RenderTemplate(self, template_name, template_values, error=None):
    response = render(
      self.request,
      template_name,
      template_values
    )
    if error:
      response.status_code = error
    return response

  def get(self, request):
    return self.RenderTemplate(
      self.template_names["get"],
      self.GetTemplateValues("get")
    )

def RequiresLogin(fun):
  def RequiresLoginDecorator(self, *args, **kwargs):
    if not self.session.get("logged_in", False):
      return redirect("/login")
    return fun(self, *args, **kwargs)
  return RequiresLoginDecorator

def RequiresModerator(fun):
  def RequiresModeratorDecorator(self, *args, **kwargs):
    if not self.session.get("logged_in", False):
      return redirect("/login")
    elif not self.user.ismoderator:
      return self.RenderTemplate("permissiondenied.html", self.GetTemplateValues(None), 403)
    return fun(self, *args, **kwargs)
  return RequiresModeratorDecorator

def RequiresAdmin(fun):
  def RequiresAdminDecorator(self, *args, **kwargs):
    if not self.session.get("logged_in", False):
      return redirect("/login")
    elif not self.user.isadmin:
      return self.RenderTemplate("permissiondenied.html", self.GetTemplateValues(None), 403)
    return fun(self, *args, **kwargs)
  return RequiresAdminDecorator

def nify_str(s):
  return s.replace("&", "").replace("$", "").replace("#", "")
