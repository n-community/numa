from google.appengine.ext import db
from google.appengine.api import memcache
import logging

from django.http import HttpResponse
from django.shortcuts import redirect

import model
import lib
from lib import query
from lib import tags

MAX_RESULTS = 1000
MAX_RESULTS_PER_PAGE = 100
NUM_SUGGESTED_TAGS = 6

class BrowsePage(lib.BaseHandler):
  def get(self, request, extension=None):
    template_values = self.GetTemplateValues("get")
    start = min(max(int(self.request.GET.get("start", 0)), 0), MAX_RESULTS)
    count = min(max(int(self.request.GET.get("count", 10)), 1),
                MAX_RESULTS_PER_PAGE,
                MAX_RESULTS - start)
    query_str = self.request.GET.get("q", "")
    lucky = bool(self.request.GET.get("ifl", False))
    is_random = bool(self.request.GET.get("random", lucky))
    
    q = query.Query(query_str, is_random, self.user)
    if start > 0 and not is_random:
      start_token = memcache.get("start_token_%s_%d" % (q.query_hash, start))
    else:
      start_token = None
    results = q.ExecuteQuery(start_token)

    if lucky:
      try:
        map = next(results)
        return redirect("/%d" % map.map_id)
      except StopIteration:
        pass

    has_more = False
    max_updated = None
    result_list = []
    try:
      if not start_token:
        for i in range(start): next(results)

      for i in range(count):
        result = next(results)
        if not max_updated or max_updated < result.lastupdated:
          max_updated = result.lastupdated
        result_list.append(result)

      if not is_random and q.start_token is not None:
        memcache.set("start_token_%s_%d" % (q.query_hash, start+count), q.start_token)
      next(results)
      has_more = True
    except StopIteration:
      pass
      
    if extension == "userlevels":
      def get_data(result):
        return result.GetMapdata()
      txt = "\n".join(get_data(x) for x in result_list)
      return HttpResponse(txt, content_type="text/plain")

    # Suggested tags
    current_tags = [x[0] for x in q.parsed_query
                    if not x[1] and model.Map.RESERVED_TAGS]
    suggested_tags = tags.SuggestTags(current_tags, NUM_SUGGESTED_TAGS - len(current_tags))
    template_values["suggested_tags"] = suggested_tags

    if self.session.get("logged_in", False) and result_list:
      if self.user.key().name() in q._positive_stars:
        # If they're searching their own favorites, obviously they're all
        # starred.
        template_values["starred"] = set([x.key().name() for x in result_list])
      else:
        fav_keys = [db.Key.from_path("Favorite", x.key().name(), parent=self.user.key())
                    for x in result_list]
        favs = model.Favorite.get(fav_keys)
        template_values["starred"] = set([x.key().name() for x in favs if x])
    
    if q.query_aborted:
      logging.info("Query aborted after evaluating %d favorites, %d maps."
                   % (q.favorites_processed, q.maps_processed))
      template_values["aborted"] = True
    else:
      logging.info("Query evaluated %d favorites, %d maps."
                   % (q.favorites_processed, q.maps_processed))
      template_values["aborted"] = False
    template_values["updated"] = max_updated
    template_values["query"] = query_str
    template_values["query_parts"] = set(q.query_parts)
    template_values["random"] = is_random
    template_values["start"] = start
    template_values["count"] = count
    template_values["results"] = result_list
    template_values["has_more"] = has_more and start + count < MAX_RESULTS
    template_values['prevstart'] = max(0, start - count)
    template_values['prevcount'] = start - template_values['prevstart']
    template_values['show_rss'] = not is_random

    if extension == ".rss":
      response = self.RenderTemplate("browse.atom", template_values)
      response.headers["Content-Type"] = "application/atom+xml"
      return response
    else:
      return self.RenderTemplate("browse.html", template_values)


class AdvancedSearchPage(lib.BaseHandler):
  def get(self, request):
    count = self.request.GET.get("count", None)
    if not count:
      template_values = self.GetTemplateValues("get")
      return self.RenderTemplate("search.html", template_values)

    parts = [
      ("tags", ""),
      ("author", "author:"),
      ("favorite", "favorites:"),
      ("not_tags", "-"),
      ("not_authors", "-author:"),
      ("not_favorite", "-favorites:"),
      ("rated", ""),
    ]
    
    query = []
    for tag, prefix in parts:
      query.extend(["%s%s" % (prefix, x.strip())
                    for x in self.request.GET.get(tag, "").split(" ") if x.strip()])

    return redirect("/browse?q=%s&count=%s" % (" ".join(query), self.request.GET.get("count", "10")))
    
    
class UnreadPage(lib.BaseHandler):
  @lib.RequiresLogin
  def get(self, request):
    template_values = self.GetTemplateValues("get")
    start = min(max(int(self.request.GET.get("start", 0)), 0), MAX_RESULTS)
    count = min(max(int(self.request.GET.get("count", 10)), 1),
                MAX_RESULTS_PER_PAGE,
                MAX_RESULTS - start)

    q = model.Map.all()
    q.filter("user =", self.user)
    q.filter("first_unread_comment >", None)
    q.order("first_unread_comment")
    result_list = q.fetch(count + 1, start)

    if len(result_list) <= count and len(result_list) != self.user.num_unread_maps:
      # Update user's unread count to take care of synchronization issues that
      # may have crept in
      def DoResetUnreadCount():
        user = model.User.get(self.user.key())
        user.num_unread_maps = len(result_list)
        user.put()
      db.run_in_transaction(DoResetUnreadCount)
      self.user.num_unread_maps = len(result_list)

    if result_list:
      fav_keys = [db.Key.from_path("Favorite", x.key().name(), parent=self.user.key())
                  for x in result_list]
      favs = model.Favorite.get(fav_keys)
      template_values["starred"] = set([x.key().name() for x in favs if x])

    template_values["start"] = start
    template_values["count"] = count
    template_values["results"] = result_list[:count]
    template_values["has_more"] = len(result_list) > count
    template_values["prevstart"] = max(0, start - count)
    template_values["prevcount"] = start - template_values["prevstart"]
    template_values["show_rss"] = False
    return self.RenderTemplate("browse.html", template_values)
