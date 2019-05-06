from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import mail
import urllib
import hashlib
import hmac
import os
import logging
import datetime

import model
import lib


class AuthServerError(Exception):
  pass


class LoginPage(lib.BaseHandler):
  def AuthenticateUser(self, username, password):
    if os.environ["SERVER_SOFTWARE"].startswith("Development/"):
      return True

    url = "http://www.harveycartel.org/metanet/n/data13/user_query_numa.php"
    content = {
      "username": username.encode("latin_1", "ignore"),
      "password": password.encode("latin_1", "ignore"),
    }
    try:
      response = urlfetch.fetch(url,
                                payload=urllib.urlencode(content),
                                method=urlfetch.POST,
                                headers={
                                  "Content-Type": "application/x-www-form-urlencoded",
                                })

      if response.status_code != 200:
        raise AuthServerError()

      response_body = dict(x.split("=") for x in response.content.split("&"))
      return response_body["authenticated"] == "1"
    except urlfetch.DownloadError:
      raise AuthServerError()

  def get(self):
    referer = self.request.headers.get("Referer", None)
    if referer and not referer.endswith("/logout") and not referer.endswith("/login"):
      self.session["redirect"] = referer
      self.session.save()
    self.RenderTemplate("login.html", self.GetTemplateValues("get"))

  def post(self):
    try:
      template_values = self.GetTemplateValues("post")

      username = self.request.POST.get("username", None)
      password = self.request.POST.get("password", None)
      if not username:
        template_values["error"] = "Invalid username or password."
        self.RenderTemplate("login.html", template_values)
        return

      user = model.User.get_by_username(username)
      pass_hash = model.User.GetPasswordHash(username, password)
      if not user or user.pass_hash != pass_hash:
        result = self.AuthenticateUser(username, password)
        if result:
          if not user:
            # New user - create them
            logging.info("First login from user '%s'." % username)
            user = model.User.new(username)
            user.pass_hash = pass_hash
            user.put()
          else:
            user.pass_hash = pass_hash
            user.put()
        else:
          template_values["error"] = "Invalid username or password."
          self.RenderTemplate("login.html", template_values)
          return
    except AuthServerError:
      template_values["error"] = ("There was an error contacting the N servers to authenticate you. "
                                  "Please try again later.")
      self.RenderTemplate("login.html", template_values)
      return

    if user.isdisabled:
      logging.info(user.disabled_until)
      if user.disabled_until and user.disabled_until < datetime.datetime.now():
        user.isdisabled = False
        user.disabled_until = None
        user.disabled_reason = None
        user.put()
      else:
        template_values["user"] = user
        self.RenderTemplate("disableduser.html", template_values)
        return

    self.user = user
    self.session['user'] = str(user.key())

    if not user.validated:
      self.redirect("/verify")
      self.session['logged_in'] = False
      self.session.save()
    else:
      redirect = self.session.get("redirect", None)
      self.session['logged_in'] = True
      if redirect:
        del self.session["redirect"]
        self.session.save()
        self.redirect(redirect)
      else:
        self.session.save()
        self.RenderTemplate("loggedin.html", self.GetTemplateValues("get"))


class VerifyPage(lib.BaseHandler):
  prohibited_domains = set(["mailinator.com"])

  def GetTemplateValues(self, method):
    template_values = super(VerifyPage, self).GetTemplateValues(method)
    template_values["invalid_email"] = False
    template_values["email_in_use"] = False
    return template_values

  def post(self):
    if not self.user:
      self.redirect("/")
      return

    template_values = self.GetTemplateValues("post")
    email = self.request.POST.get("email", "")
    if "@" not in email or email.split("@")[1] in self.prohibited_domains:
      template_values["invalid_email"] = True
      self.RenderTemplate("validateuser.html", template_values)
      return

    other_account = model.User.all().filter("email =", email).get()
    if other_account and other_account.key() != self.user.key():
      template_values["email_in_use"] = True
      self.RenderTemplate("validateuser.html", template_values)
      return

    self.user.email = email
    self.user.put()
    template_values["email"] = email
    template_values["email_hash"] = self.user.GetEmailHash()
    email_body = webapp.template.render(self.GetTemplatePath("activation.txt"),
                                        template_values)
    mail.send_mail(sender="contact.nmaps@gmail.com",
                   to="%s <%s>" % (self.user.username,
                                   self.user.email),
                   subject="NUMA Account Activation",
                   body=email_body)
    logging.info("Sent validation email: %s" % (email_body,))
    self.RenderTemplate("emailsent.html", template_values)

  def get(self):
    template_values = self.GetTemplateValues("get")
    username = self.request.GET.get("username", "")
    user = model.User.get_by_username(username)
    email_hash = self.request.GET.get("email_hash", "")
    if not user or not user.email or user.GetEmailHash() != email_hash:
      if not self.user:
        self.RenderTemplate("requireslogin.html", template_values)
      else:
        self.RenderTemplate("validateuser.html", template_values)
      return
    user.validated = True
    user.put()

    self.user = user
    self.session["user"] = str(user.key())
    self.session["logged_in"] = True
    self.session.save()
    logging.info("User \"%s\" validated successfully." % user.username)
    self.RenderTemplate("validated.html", self.GetTemplateValues("get"))


class LogoutPage(lib.BaseHandler):
  def get(self):
    if self.session.get("logged_in", False):
      del self.session["user"]
      self.session["logged_in"] = False
      self.session.save()
      self.RenderTemplate("loggedout.html", self.GetTemplateValues("get"))
    else:
      self.redirect("/")
