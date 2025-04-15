import lib

class NotFoundPage(lib.BaseHandler):
  def get(self, request):
    template_values = self.GetTemplateValues("get")
    return self.RenderTemplate("nosuchpage.html", template_values, 404)
