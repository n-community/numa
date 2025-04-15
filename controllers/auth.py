from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import mail
from urllib.parse import urlencode
from django.shortcuts import redirect
from django.template.loader import render_to_string
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
    if not os.getenv('GAE_ENV', '').startswith("standard"):
      return True

    url = "http://www.harveycartel.org/metanet/n/data13/user_query_numa.php"
    content = {
      "username": username.encode("latin_1", "ignore"),
      "password": password.encode("latin_1", "ignore"),
    }
    try:
      response = urlfetch.fetch(
        url,
        payload=urlencode(content),
        method=urlfetch.POST,
        headers={ "Content-Type": "application/x-www-form-urlencoded" }
      )

      if response.status_code != 200:
        raise AuthServerError()

      response_body = dict(x.split("=") for x in response.content.decode().split("&"))
      return response_body["authenticated"] == "1"
    except urlfetch.DownloadError:
      raise AuthServerError()


  def get(self, request):
    referer = self.request.headers.get("Referer", None)
    if referer and not referer.endswith("/logout") and not referer.endswith("/login"):
      self.session["redirect"] = referer
    return self.RenderTemplate("login.html", self.GetTemplateValues("get"))


  def post(self, request):
    try:
      template_values = self.GetTemplateValues("post")
      username = self.request.POST.get("username", None)
      password = self.request.POST.get("password", None)

      if not username:
        template_values["error"] = "Invalid username or password."
        return self.RenderTemplate("login.html", template_values)

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
          return self.RenderTemplate("login.html", template_values)
    except AuthServerError:
      template_values["error"] = (
        "There was an error contacting the N servers to authenticate you. "
        "Please try again later."
      )
      return self.RenderTemplate("login.html", template_values)

    if user.isdisabled:
      logging.info(user.disabled_until)
      if user.disabled_until and user.disabled_until < datetime.datetime.utcnow():
        user.isdisabled = False
        user.disabled_until = None
        user.disabled_reason = None
        user.put()
      else:
        template_values["user"] = user
        return self.RenderTemplate("disableduser.html", template_values)

    self.user = user
    self.session['user'] = str(user.key())

    if not user.validated:
      self.session['logged_in'] = False
      return redirect("/verify")
    else:
      redir = self.session.get("redirect", None)
      self.session['logged_in'] = True
      if redir:
        del self.session["redirect"]
        return redirect(redir)
      else:
        return self.RenderTemplate("loggedin.html", self.GetTemplateValues("get"))


class VerifyPage(lib.BaseHandler):
  prohibited_domains = set(["mailinator.com"])

  def GetTemplateValues(self, method):
    template_values = super(VerifyPage, self).GetTemplateValues(method)
    template_values["invalid_email"] = False
    template_values["email_in_use"] = False
    return template_values

  def post(self, request):
    if not self.user:
      return redirect("/")

    template_values = self.GetTemplateValues("post")
    email = self.request.POST.get("email", "")
    if "@" not in email or email.split("@")[1] in self.prohibited_domains:
      template_values["invalid_email"] = True
      return self.RenderTemplate("validateuser.html", template_values)

    other_account = model.User.all().filter("email =", email).get()
    if other_account and other_account.key() != self.user.key():
      template_values["email_in_use"] = True
      return self.RenderTemplate("validateuser.html", template_values)

    self.user.email = email
    self.user.put()
    template_values["email"] = email
    template_values["email_hash"] = self.user.GetEmailHash()

    email_body = render_to_string(
      "activation.txt",
      template_values
    )

    # only send a real email on production.
    if os.getenv("GAE_ENV", "").startswith("standard"):
      mail.send_mail(
        sender="contact.nmaps@gmail.com",
        to="%s <%s>" % (self.user.username, self.user.email),
        subject="NUMA Account Activation",
        body=email_body
      )
    else:
      # logging.info doesn't seem to go to the console, so print out the link for dev:
      print("Use this link to register. Remember to replace nmaps.net with your local url:")
      print(email_body)
      
    logging.info("Sent validation email: %s" % (email_body))
    return self.RenderTemplate("emailsent.html", template_values)


  def get(self, request):
    template_values = self.GetTemplateValues("get")
    username = self.request.GET.get("username", "")
    user = model.User.get_by_username(username)
    email_hash = self.request.GET.get("email_hash", "")
    if not user or not user.email or user.GetEmailHash() != email_hash:
      if not self.user:
        return self.RenderTemplate("requireslogin.html", template_values)
      else:
        return self.RenderTemplate("validateuser.html", template_values)
    user.validated = True
    user.put()

    self.user = user
    self.session["user"] = str(user.key())
    self.session["logged_in"] = True
    logging.info("User \"%s\" validated successfully." % user.username)
    return self.RenderTemplate("validated.html", self.GetTemplateValues("get"))


class LogoutPage(lib.BaseHandler):
  def get(self, request):
    if self.session.get("logged_in", False):
      del self.session["user"]
      self.session["logged_in"] = False
      return self.RenderTemplate("loggedout.html", self.GetTemplateValues("get"))
    else:
      return redirect("/")
