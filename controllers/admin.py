import lib
import model

from django.shortcuts import redirect

class ModerationQueuePage(lib.BaseHandler):
  @lib.RequiresModerator
  def get(self, request):
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
    return self.RenderTemplate("moderationqueue.html", template_values)
    
class NewsPostPage(lib.BaseHandler):
  @lib.RequiresAdmin
  def get(self, request):
    template_values = self.GetTemplateValues("get")
    return self.RenderTemplate("newspost.html", template_values)

  @lib.RequiresAdmin
  def post(self, request):
    title = self.request.POST.get("title", "")
    text = self.request.POST.get("text", "")
    if not title or not text:
      template_values = self.GetTemplateValues("get")
      template_values["title"] = title
      template_values["text"] = text
      template_values["error"] = "Both title and text are required."
      return self.RenderTemplate("newspost.html", template_values)

    post = model.News(title=title, text=text)
    post.put()
    model.AdminLog.create(self, ref=post)

    return redirect("/")
