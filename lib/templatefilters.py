from django import template
import datetime
from urllib.parse import quote

from . import postmarkup

register = template.Library()

@register.filter(name='isin')
def isin(value, arg):
  return value in arg

@register.filter(name='equals')
def equals(value, arg):
  return value == arg

@register.filter(name='sub')
def sub(value, arg):
  return value-arg

@register.filter(name="date_relative")
def date_relative(value):
  # utcnow is slated for deprecation; gotta move to datetime.datetime.now(datetime.UTC) eventually
  # or: from datetime import datetime, timezone; datetime.now(timezone.utc)
  interval = datetime.datetime.utcnow() - value
  total_seconds = interval.total_seconds()
  seconds = abs(int(total_seconds))

  # disableduser page uses future dates
  ago = ""
  if total_seconds > 0:
    ago = " ago"

  if seconds >= 172800:
    return value.strftime("%Y-%m-%d")
  elif seconds > 7200:
    val = int(seconds / 3600)
    return "{} hours{}".format(val, ago)
  elif seconds > 120:
    val = int(seconds / 60)
    return "{} mins{}".format(val, ago)
  elif seconds > 1:
    return "{} secs{}".format(seconds, ago)
  else:
    return "1 second{}".format(ago)

register.filter("bbcode", postmarkup.render_bbcode)

@register.filter(name="add_tag")
def add_tag(tags, tag):
  new_query = set([tag])
  new_query.update(tags)
  return " ".join(new_query)

@register.filter(name="remove_tag")
def remove_tag(tags, tag):
  new_query = set(tags)
  new_query.remove(tag)
  return " ".join(new_query)

@register.filter(name="urlcat")
def urlcat(base, ext):
  return base + quote(ext)

@register.tag(name="contextual_link")
def do_contextual_link(parser, token):
  try:
    tag_name, path, selected_class = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError("%r tag requires exactly 2 arguments." % token.contents[0])

  nodelist = parser.parse("endlink")
  parser.delete_first_token()
  path_qs = template.Variable("path_qs")
  return LinkNode(path, path_qs, selected_class, nodelist)

class LinkNode(template.Node):
  def __init__(self, path, path_qs, selected_class, nodelist):
    self.path = path
    self.path_qs = path_qs
    self.selected_class = selected_class
    self.nodelist = nodelist

  def render(self, context):
    script_name = self.path_qs.resolve(context)
    if script_name == self.path:
      return "<a class=\"%s\" href=\"%s\">%s</a>" % (self.selected_class, self.path, self.nodelist.render(context))
    else:
      return "<a href=\"%s\">%s</a>" % (self.path, self.nodelist.render(context))
