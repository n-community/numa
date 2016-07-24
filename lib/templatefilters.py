from google.appengine._internal.django import template
import datetime
import urllib
import logging

import postmarkup

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
  interval = datetime.datetime.now() - value
  seconds = interval.days * 86400 + interval.seconds
  if seconds >= 172800:
    return value.strftime("%Y-%m-%d")
  elif seconds > 7200:
    val = int(seconds / 3600)
    return "%d hours ago" % val
  elif seconds > 120:
    val = int(seconds / 60)
    return "%d mins ago" % val
  elif seconds > 1:
    return "%d secs ago" % seconds
  else:
    return "1 second ago"

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
  return base + urllib.quote(ext)

@register.tag(name="contextual_link")
def do_contextual_link(parser, token):
  try:
    tag_name, path, selected_class = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError("%r tag requires exactly 2 arguments." % token.contents[0])
  nodelist = parser.parse("endlink")
  parser.delete_first_token()
  return LinkNode(path, selected_class, nodelist)

class LinkNode(template.Node):
  def __init__(self, path, selected_class, nodelist):
    self.path = path
    self.selected_class = selected_class
    self.nodelist = nodelist

  def render(self, context):
    script_name = template.resolve_variable('path_qs', context)
    if script_name == self.path:
      return "<a class=\"%s\" href=\"%s\">%s</a>" % (self.selected_class, self.path, self.nodelist.render(context))
    else:
      return "<a href=\"%s\">%s</a>" % (self.path, self.nodelist.render(context))
