from google.appengine.ext import db

import model
import lib

class SundayNPage(lib.BaseHandler):
  def get(self, request, num=None, action=None):
    template_values = self.GetTemplateValues("get")
    last_sn = model.SundayN.all().order("-number").get()    
    if num:
      sn = model.SundayN.get_by_key_name("_" + num)
    else:
      sn = last_sn
      
    if not sn:
      return self.RenderTemplate("nosuchpage.html", template_values, 404)

    template_values['sundayn'] = sn
    template_values['last_sundayn'] = last_sn
    
    if action == "feedback":
      return self.ShowFeedback(template_values, sn)
    else:
      return self.ShowSundayN(template_values, sn)

  def ShowSundayN(self, template_values, sn):
    template_values["archive_nums"] = range(1, template_values["last_sundayn"].number + 1)
    return self.RenderTemplate("sundayn.html", template_values)

  def ShowFeedback(self, template_values, sn):
    q = model.Comment.all()
    q.ancestor(sn)
    q.order("-lastupdated")
    template_values["comments"] = q
    return self.RenderTemplate("sundayncomments.html", template_values)

