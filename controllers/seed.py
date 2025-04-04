from google.appengine.ext import db

from django.shortcuts import redirect

import model
import lib

from seed_data.users import user_seeds
from seed_data.sundayn import sundayn_seeds
from seed_data.sundaynfeedback import sundaynfeedback_seeds
from seed_data.maps import map_seeds


class SeedPage(lib.BaseHandler):
  def get(self, request):
    return
    if os.getenv("GAE_ENV", "").startswith("standard"):
      return redirect("/")
    # make it not run if any user exists, just in case? + instructions to delete database
    # self.seed_users()
    # self.seed_sundayn()
    # self.seed_sundaynfeedback()

    # self.seed_maps()
    # self.seed_comments()
    # self.seed_favorites() # ???
    return redirect("/sundayn")

  def seed_users(self):
    # add isdisabled users later, or disable them at the end, i dunno how that interferes with adding maps
    # also canvote
    # maybe we can just do all of this as mods, so no need to seed with it?
    # or create some new ones without maps
    for u in user_seeds:
      username = u["username"]
      password = "asdf"
      email = "%s@fako.com" % username

      user = model.User.new(username)

      user.pass_hash = model.User.GetPasswordHash(username, password)
      user.email = email
      user.validated = True

      for key in ["isadmin", "ismoderator", "canreview"]:
        value = u.get(key)
        if value:
          setattr(user, key, value)

      user.put()

  def seed_maps(self):
    # let's add some that have been reported if that's not hard
    return

  def seed_comments(self):
    # let's add some that have been reported if that's not hard
    return

  def seed_sundayn(self):
    for i, text in enumerate(sundayn_seeds, start=1):
      key_name = "_%s" % i
      model.SundayN(
        key_name=key_name,
        number=i,
        text=text
      ).put()
  
  def seed_sundaynfeedback(self):
    for feedback in sundaynfeedback_seeds:
      username = feedback.username
      parent_key = db.Key.from_path(
        "SundayN",
        "_{}".format(feedback.parent_key)
      )

      author = model.User.get_by_username(username)
      sundayn = model.SundayN.get(parent_key)

      model.Comment(
        author=author,
        parent=sundayn,
        title=feedback.title,
        text=feedback.text
      ).put()
    return