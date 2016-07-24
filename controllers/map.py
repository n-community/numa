from google.appengine.api import files
from google.appengine.api import images
from google.appengine.ext import blobstore
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.api import urlfetch

import urllib
import hashlib
import logging
import os
import random
import datetime
import math
import uuid
import zlib

import cloudstorage
import model
import lib
from lib import imagegen

COMMENTS_PER_PAGE = 40
REVIEW_INTERVAL = datetime.timedelta(hours=72)

def create_map_image(mapdata):
  # Create the map images
  try:
    level_image = imagegen.generate_level_image(*imagegen.parse_level(mapdata))
    return level_image
  except Exception, ex:
    logging.exception("Failed to generate level image.")
    return None

def create_map_blob(mapdata):
  level_image = create_map_image(mapdata)
  if not level_image: return None
  try:
    file_name = "/nmapsdotnet.appspot.com/maps/%s.png" % uuid.uuid4()
    with cloudstorage.open(file_name, "w") as f:
      level_image.save(f, "PNG")
    blob_key = blobstore.create_gs_key("/gs" + file_name)
    return images.get_serving_url(blob_key)
  except Exception:
    logging.exception("Failed to save level image.")
    return None


class MapBase(lib.BaseHandler):
  def AddOrEditMap(self, form_template, map=None):
    template_values = self.GetTemplateValues("post")

    name = self.request.POST.get("name", "").strip()
    description = self.request.POST.get("description", "").strip()
    tags = self.request.POST.getall("tags")
    tags = list(set([model.Tag.normalise(x) for x in tags if x]))
    mapdata = self.request.POST.get("mapdata", "")
    disableratings = self.request.POST.get("disableratings", None)

    template_values.update(self.request.POST)
    template_values["tags"] = tags + [""] * (5 - len(tags))

    if not name or not description or not tags or (not map and not mapdata):
      template_values["error"] = "Please fill in all the required fields."
      template_values["resubmit"] = True
      self.RenderTemplate(form_template, template_values)
      return

    if len(name) > 60 or len(description) > 4000:
      template_values["error"] = ("Please limit the title and description to "
                                  "60 and 4000 characters, respectively.")
      template_values["resubmit"] = True
      self.RenderTemplate("submitform.html", template_values)
      return

    # Update map data for new submissions and unrated maps
    if mapdata and (not map or not map.IsRated()):
      try:
        mapdata = model.Map.ValidateMapData(mapdata)
        template_values['mapdata'] = mapdata
        template_values['compresseddata'] = zlib.compress(mapdata).encode("base64")
      except model.InvalidMapError, e:
        template_values["error"] = str(e)
        template_values["resubmit"] = True
        self.RenderTemplate(form_template, template_values)
        return

      mapdata_hash = hashlib.sha1(mapdata).hexdigest()
      dup_map = model.Map.all().filter("mapdata_hash =", mapdata_hash).get()
      if dup_map and (not map or dup_map.key() != map.key()):
        template_values["error"] = ("This map already exists in the database. "
                                    "Please submit a NEW map.")
        template_values["resubmit"] = True
        self.RenderTemplate(form_template, template_values)
        return

    if not map and ("confirm" not in self.request.POST):
      self.RenderTemplate("confirmsubmission.html", template_values)
      return

    if map:
      map_id = map.map_id
    else:
      map_id = model.Sequence.GetNextId("map_id")

    # Regenerate images if it's a new map or the data changed
    if not map or (mapdata and not map.IsRated() and mapdata_hash != map.mapdata_hash):
      image_url = create_map_blob(mapdata)
    else:
      image_url = map.image_url

    if not map:
      # New map
      map = model.Map(key_name=model.Map.get_key_name(map_id),
                      float_num=map_id,
                      name=name,
                      description=description,
                      mapdata=mapdata,
                      mapdata_hash=mapdata_hash,
                      user=self.user,
                      disableratings=disableratings is not None,
                      random=random.random(),
                      image_url=image_url)
      self.user.RecordNewMap()
    else:
      # Edit map
      map.name = name
      map.description = description
      map.lastupdated = datetime.datetime.now()
      if mapdata and not map.IsRated():
        map.mapdata = mapdata
        map.mapdata_hash = mapdata_hash
        map.image_url = image_url
    map.SetTags(tags)
    map.put()

    self.redirect("/map/%d" % map_id)

class MapPage(MapBase):
  def UserHasVoted(self, map):
    if self.session.get("logged_in", False):
      vote_key = db.Key.from_path("Map", map.key().name(),
                                  "Vote", self.user.key().name())
      return model.Vote.get(vote_key) != None
    else:
      return True

  def get(self, map_id, action=None):
    template_values = self.GetTemplateValues("get")

    map = model.Map.get_by_map_id(int(map_id))
    if not map:
      self.response.set_status(404)
      self.RenderTemplate("nosuchmap.html", template_values)
      return

    methods = {
      None: self.RenderMapPage,
      "edit": self.ShowEditForm,
      "data": self.ShowDataPage,
      "delete": self.ShowDeletePage,
      "review": self.ShowReviewPage,
      "comments": self.ShowCommentsPage,
    }

    template_values["map"] = map
    template_values["mapdata"] = map.GetMapdata()

    if action in methods:
      methods[action](map, template_values)
    else:
      self.RenderTemplate("internalerror.html", template_values)

  def GetPagesArray(self, count, start, page_len):
    return [page_len*i if page_len*i != start else None
            for i in range(int(math.ceil(count / page_len)))]

  def RenderMapPage(self, map, template_values):
    if (self.session.get("logged_in", False)
        and self.user.key() == map._user
        and map.first_unread_comment):
      # Reset unread counts
      template_values['first_unread'] = map.first_unread_comment
      map.MarkAsRead()
      self.user.num_unread_maps -= 1

    template_values["user_has_voted"] = self.UserHasVoted(map)

    q = model.Comment.all().ancestor(map).order("-lastupdated")
    comments = q.fetch(COMMENTS_PER_PAGE + 1)
    template_values["comments"] = comments[:COMMENTS_PER_PAGE]
    template_values["count"] = COMMENTS_PER_PAGE
    template_values["has_more"] = len(comments) > COMMENTS_PER_PAGE

    if self.session.get("logged_in", False):
      template_values["faved"] = model.Favorite.Exists(self.user.key(),
                                                       map.key())
    show_featured = (map.featured_date
                     and (map.featured_date <= datetime.datetime.today()
                          or (self.session.get("logged_in", False)
                              and (self.user.isadmin or self.user.canreview))))
    template_values["show_featured"] = show_featured
    template_values["future_featured"] = (show_featured and map.featured_date and
                                          map.featured_date > datetime.datetime.today())
    template_values["comment_page_count"] = int(math.ceil(map.comment_count / COMMENTS_PER_PAGE))
    template_values["pages"] = self.GetPagesArray(map.comment_count, 0, COMMENTS_PER_PAGE)

    q = model.Map.all()
    q.filter("user =", map.user)
    q.filter("unlisted =", False)
    q.filter("float_num <", map.float_num)
    q.order("-float_num")
    other_maps = q.fetch(6)
    other_maps.reverse()
    template_values["other_maps"] = other_maps

    self.RenderTemplate("map.html", template_values)

  @lib.RequiresLogin
  def ShowEditForm(self, map, template_values):
    template_values["tags"] = map.GetUserTags()
    template_values["tags"] += [""] * (5 - min(5, len(template_values["tags"])))
    self.RenderTemplate("editmap.html", template_values)

  def ShowDataPage(self, map, template_values):
    self.response.headers["Content-Type"] = "text/plain"
    self.response.out.write(template_values['mapdata'])

  @lib.RequiresLogin
  def ShowDeletePage(self, map, template_values):
    if self.user.key() != map.user.key() and not self.user.ismoderator:
      self.redirect("/map/%d" % map.map_id)
    template_values['show_delist'] = not map.unlisted
    template_values['show_moddelist'] = (map.unlisted
                                         and not map.moderator_unlisted
                                         and map.user.key() != self.user.key()
                                         and self.user.ismoderator)
    self.RenderTemplate("confirmdelete.html", template_values)

  @lib.RequiresLogin
  def ShowReviewPage(self, map, template_values):
    if not self.user.canreview and not self.user.isadmin:
      self.response.set_status(403)
      self.RenderTemplate("permissiondenied.html", template_values)
    elif not self.user.isadmin and map.IsFeatured():
      self.RenderTemplate("cannotreview.html", template_values)
    elif not self.user.isadmin and map.featured_by and map._featured_by != self.user.key():
      self.RenderTemplate("cannotreview.html", template_values)
    else:
      if map.featured_text:
        template_values['review'] = map.featured_text
      self.RenderTemplate("reviewmap.html", template_values)

  def ShowCommentsPage(self, map, template_values):
    start = int(self.request.GET.get("start", 0))
    count = int(self.request.GET.get("count", COMMENTS_PER_PAGE))

    q = model.Comment.all().ancestor(map).order("-lastupdated")
    comments = q.fetch(count + 1, start)
    template_values["comments"] = comments[:count]
    template_values["has_more"] = len(comments) > count
    template_values["start"] = start
    template_values["count"] = count
    template_values["prevstart"] = max(0, start - count)
    template_values["prevcount"] = start - template_values["prevstart"]
    template_values["comment_page_count"] = int(math.ceil(map.comment_count / count))
    template_values["pages"] = self.GetPagesArray(map.comment_count, start, count)
    self.RenderTemplate("comments.html", template_values)

  def post(self, map_id, action=None):
    template_values = self.GetTemplateValues("post")
    map = model.Map.get_by_key_name(model.Map.get_key_name(int(map_id)))
    if not map:
      self.RenderTemplate("nosuchmap.html", template_values)
      return

    methods = {
      "submit": self.NewComment,
      "rate": self.RateMap,
      "edit": self.EditMap,
      "addstar": self.AddStar,
      "remstar": self.RemoveStar,
      "delete": self.DelistMap,
      "reportabuse": self.ReportAbuse,
      "deletecomment": self.DeleteComment,
      "clearflag": self.ClearFlag,
      "review": self.SubmitReview,
    }
    if action in methods:
      methods[action](map, template_values)
    else:
      self.RenderTemplate("internalerror.html", template_values)

  @lib.RequiresLogin
  def NewComment(self, map, template_values):
    title = self.request.POST.get("title", "").strip()
    text = self.request.POST.get("text", "").strip()
    demodata = self.request.POST.get("demodata", None)

    if not text:
      template_values["error"] = "Please fill in the body of your comment."
      self.RenderTemplate("invalidcomment.html", template_values)
      return

    if len(text) > 2500:
      template_values["error"] = "Please limit your comment to 2500 characters."
      self.RenderTemplate("invalidcomment.html", template_values)
      return

    if len(title) > 256:
      template_values["error"] = "Please limit your title to 256 characters."
      self.RenderTemplate("invalidcomment.html", template_values)
      return

    if demodata and not model.Comment.ValidateDemo(demodata):
      template_values["error"] = "The demo data is invalid."
      self.RenderTemplate("invalidcomment.html", template_values)
      return

    comment = model.Comment.new(map.key(),
                                author=self.user,
                                title=title,
                                text=text,
                                demodata=demodata)

    self.redirect("/map/%d#%d" % (map.map_id, comment.key().id()))

  @lib.RequiresLogin
  def RateMap(self, map, template_values):
    rating = self.request.POST.get("rating", False)
    if rating:
      rating = int(rating)
      if (self.user.canvote and not self.UserHasVoted(map)
          and self.user.key() != map.user.key()
          and rating >= 0 and rating <= 5
          and not map.disableratings and not map.unlisted):
        map.RecordVote(self.user.key(), rating)

    self.redirect("/map/%d" % map.map_id)

  @lib.RequiresLogin
  def EditMap(self, map, template_values):
    if(map.user.key() == self.user.key() or self.user.isadmin):
      self.AddOrEditMap("editmap.html", map=map)
      if self.user.isadmin:
        model.AdminLog.create(self, ref=map)
    else:
      self.redirect("/map/%d" % (map.map_id, ))

  @lib.RequiresLogin
  def AddStar(self, map, template_values):
    map.AddStar(self.user.key())
    self.response.out.write("Content-Type: text/plain\n\n");
    self.response.out.write("Added star!");

  @lib.RequiresLogin
  def RemoveStar(self, map, template_values):
    map.RemoveStar(self.user.key())
    self.response.out.write("Content-Type: text/plain\n\n");
    self.response.out.write("Removed star!")

  def _UpdateMapTotals(self, map, delta):
    user = model.User.get(map._user)
    user.map_count += delta
    if map.rated:
      user.rated_map_count += delta
      user.rating_histogram[min(int(round(map.rating)), 4)] += delta
    user.ratings += delta * map.votes
    if map.featured_by:
      user.featured_map_count += delta
    user.put()

  @lib.RequiresLogin
  def DelistMap(self, map, template_values):
    if self.user.key() != map.user.key() and not self.user.ismoderator:
      self.redirect("/map/%d" % map.map_id)
    if self.request.POST.get("delist", False):
      map.unlisted = True
      if self.user.ismoderator and self.user.key() != map.user.key():
        model.AdminLog.create(self, ref=map)
        map.moderator_unlisted = True
        map.reported = False
      map.put()
      db.RunInTransaction(self._UpdateMapTotals, map, -1)
    elif self.request.POST.get("relist", False):
      map.unlisted = False
      if self.user.ismoderator:
        model.AdminLog.create(self, ref=map)
        map.moderator_unlisted = False
      map.put()
      db.RunInTransaction(self._UpdateMapTotals, map, 1)
    self.redirect("/map/%d" % map.map_id)

  @lib.RequiresLogin
  def ReportAbuse(self, map, template_values):
    comment_id = self.request.POST.get("commentid", None)
    if comment_id:
      comment = model.Comment.get_by_comment_id(map, int(comment_id))
      if not comment.reported:
        comment.reported = True
        comment.reported_by = self.user
        comment.put()
    else:
      if not map.reported:
        map.reported = True
        map.reported_by = self.user
      map.put()
    self.response.out.write("Reported!")

  def _UpdateCommentCount(self, map_id, delta):
    map = model.Map.get(map_id)
    map.comment_count += delta
    map.put()

  @lib.RequiresModerator
  def DeleteComment(self, map, template_values):
    comment_id = self.request.POST.get("commentid", None)
    if not comment_id:
      self.status_code(500)
      self.response.out.write("Could not find comment id.")
      return
    comment = model.Comment.get_by_comment_id(map, int(comment_id))
    db.RunInTransaction(self._UpdateCommentCount, comment.key().parent(), -1)
    comment.delete()
    model.AdminLog.create(self, ref=map)
    self.response.out.write("Deleted!")

  @lib.RequiresModerator
  def ClearFlag(self, map, template_values):
    comment_id = self.request.POST.get("commentid", None)
    if comment_id:
      comment = model.Comment.get_by_comment_id(map, int(comment_id))
      comment.reported = False
      comment.put()
      model.AdminLog.create(self, ref=comment)
    else:
      map.reported = False
      map.put()
      model.AdminLog.create(self, ref=map)
    self.response.out.write("Un-reported!")

  @lib.RequiresLogin
  def SubmitReview(self, map, template_values):
    template_values["map"] = map

    if not self.user.canreview and not self.user.isadmin:
      self.response.set_status(403)
      self.RenderTemplate("permissiondenied.html", template_values)
    elif not self.user.isadmin and map.IsFeatured():
      self.RenderTemplate("cannotreview.html", template_values)
    elif not self.user.isadmin and map.featured_by and map._featured_by != self.user.key():
      self.RenderTemplate("cannotreview.html", template_values)
    else:
      if self.request.POST.get("delete", False) and map.featured_by:
        # Deleting review

        # Move everything after this map forward
        if not map.IsFeatured():
          maps = model.Map.all().filter("featured_date >", map.featured_date).order("featured_date").fetch(100)
          gap = map.featured_date
          gapidx = -1
          # Move any reviews by the author of the deleted review forward
          for i, m in enumerate(maps):
            if m.featured_by == map.featured_by:
              newgap = m.featured_date
              m.featured_date = gap
              m.put()
              gap = newgap
              gapidx = i

          # Move any remaining maps forward
          for i in range(gapidx+1, len(maps)):
            newgap = maps[i].featured_date
            maps[i].featured_date = gap
            maps[i].put()
            gap = newgap

        # Remove the review
        map.featured_by = None
        map.featured_text = None
        map.featured_date = None
        map.put()

        self.RenderTemplate("reviewdeleted.html", template_values)
      else:
        review_text = self.request.POST.get("review", "")
        review_len = len(review_text.split())
        if review_len < 50 or review_len > 100:
          template_values["error"] = ("Your review is %s words long. "
                                      "Please ensure your review is between 50 "
                                      "and 100 words long." % (review_len))
          template_values["review"] = review_text
          self.RenderTemplate("reviewmap.html", template_values)
          return

        if not map.featured_date:
          # New review
          latest_review = model.Map.all().order("-featured_date").get()
          review_date = max(datetime.datetime.now(), latest_review.featured_date + REVIEW_INTERVAL)

          map.featured_date = review_date
          map.featured_by = self.user
        map.featured_text = review_text
        map.put()
        self.RenderTemplate("reviewsubmitted.html", template_values)

class SubmitPage(MapBase):
  def GetTemplateValues(self, method):
    template_values = super(SubmitPage, self).GetTemplateValues(method)
    template_values["resubmit"] = False
    template_values["tags"] = [""] * 5
    return template_values

  @lib.RequiresLogin
  def get(self):
    template_values = self.GetTemplateValues("get")
    self.RenderTemplate("submitform.html", template_values)

  @lib.RequiresLogin
  def post(self):
    self.AddOrEditMap("submitform.html")


class MapRedirectPage(lib.BaseHandler):
    def get(self, map_id, action=None):
      if action:
        self.redirect("/%d/%s" % (int(map_id), action))
      else:
        self.redirect("/%d" % (int(map_id),))


class PreviewPage(lib.BaseHandler):
    def get(self):
        mapdata = zlib.decompress(self.request.GET['mapdata'].decode("base64"))
        thumb = self.request.GET.get('thumb')
        image = create_map_image(mapdata)
        if thumb:
            image = image.resize((132, 100))
        self.response.content_type = "image/png"
        image.save(self.response.out, "PNG")
