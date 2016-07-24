from google.appengine.ext import db

import lib
import model

class ModerationQueuePage(lib.BaseHandler):
  @lib.RequiresModerator
  def get(self):
    template_values = self.GetTemplateValues("get")
    count = int(self.request.GET.get("count", 20))
    q = model.Map.all()
    q.filter("reported =", True)
    q.order("-created")
    template_values["maps"] = q.fetch(count)
    if len(template_values["maps"]) < count:
      q = model.Comment.all()
      q.filter("reported =", True)
      q.order("-lastupdated")
      comments = q.fetch(count - len(template_values["maps"]))
      template_values["comments"] = q.fetch(count - len(template_values["maps"]))
    self.RenderTemplate("moderationqueue.html", template_values)
    
class NewsPostPage(lib.BaseHandler):
  @lib.RequiresAdmin
  def get(self):
    template_values = self.GetTemplateValues("get")
    self.RenderTemplate("newspost.html", template_values)

  @lib.RequiresAdmin
  def post(self):
    title = self.request.POST.get("title", "")
    text = self.request.POST.get("text", "")
    if not title or not text:
      template_values = self.GetTemplateValues("get")
      template_values.update(self.request.POST)
      template_values["error"] = "Both title and text are required."
      self.RenderTemplate("newspost.html", template_values)
      return

    post = model.News(title=title, text=text)
    post.put()
    model.AdminLog.create(self, ref=post)

    self.redirect("/")
