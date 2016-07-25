from google.appengine.ext import db
import logging
import datetime

import model
import lib

MAX_RESULTS = 1000
MAX_RESULTS_PER_PAGE = 100

class FeaturedPage(lib.BaseHandler):
  def get(self, atom=None):
    template_values = self.GetTemplateValues("get")
    start = min(max(int(self.request.GET.get("start", 0)), 0), MAX_RESULTS)
    count = min(max(int(self.request.GET.get("count", 10)), 1),
                MAX_RESULTS_PER_PAGE,
                MAX_RESULTS - start)
    future = (bool(self.request.GET.get("future", False))
              and self.session.get("logged_in", False)
              and (self.user.isadmin or self.user.canreview))

    q = model.Map.all()
    today = datetime.datetime.today()

    results = None
    if future:
      q.filter("featured_date >", today)
      q.order("featured_date")
      results = q.fetch(100)
    else:
      q.filter("featured_date >", None)
      q.filter("featured_date <=", today)
      q.order("-featured_date")
      results = q.fetch(count + 1, start)


    if atom:
      if results:
        template_values["updated"] = max(results, key=lambda x:x.featured_date).featured_date
      template_values["results"] = results[:count]
      self.RenderTemplate("featured.atom", template_values)
    else:
      template_values["start"] = start
      template_values["count"] = count
      template_values["future"] = future
      template_values["results"] = results[:count]
      template_values["has_more"] = len(results) > count and start + count < MAX_RESULTS
      template_values['prevstart'] = max(0, start - count)
      template_values['prevcount'] = start - template_values['prevstart']
      self.RenderTemplate("featuredmaps.html", template_values)
