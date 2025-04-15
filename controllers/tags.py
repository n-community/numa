from google.appengine.ext import db

import model
import lib
from lib.tags import SuggestTags

class SuggestTagsPage(lib.BaseHandler):
  def get(self, request):
    tags = self.request.GET.get("tags", "").split(" ")
    tags = [x for x in tags if x]
    prefix = self.request.GET.get("prefix", "")
    count = min(int(self.request.GET.get("count", 10)), 10)
    suggested_tags = SuggestTags(tags, count, prefix)
    return self.RenderTemplate("suggesttags.html", {"tags": suggested_tags})

