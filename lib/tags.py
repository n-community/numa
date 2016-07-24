from google.appengine.ext import db
import logging

import model
UNICODE_MAX = u"\xEF\xBF\xBD"

def SuggestTags(tag_list, count, prefix=""):
  """Suggests similar tags to try."""
  if len(tag_list) >= 5: return []
  if not tag_list:
    q = model.Tag.all()
    q.filter("reccommend =", True)
    if prefix:
      q.filter("name >", prefix)
      q.filter("name <", prefix + UNICODE_MAX)
      tags = sorted(q.fetch(50), key=lambda x:x.count)
    else:
      q.order("-count")
      tags = q.fetch(count + 1)
    return [x.name for x in tags if x.name != "bitesized"][:count]
  else:
    q = model.TagJoin.all()
    tagstr = " ".join(sorted([model.Tag.normalise(x) for x in tag_list]))
    q.filter("prefix =", tagstr)
    if prefix:
      q.filter("tag >", prefix)
      q.filter("tag <", prefix + UNICODE_MAX)
      tags = sorted(q.fetch(50), key=lambda x:x.count)
    else:
      q.order("-count")
      tags = q.fetch(count + 1)
    return [x.tag for x in tags if x.tag != "bitesized"][:count]
