from google.appengine.ext import db

from django.http import HttpResponse

import json as simplejson

import logging
import lib
import model


def isodate(dt):
  if not dt:
    return dt
  return dt.isoformat()


def prefetch_refprops(entities, *props):
    fields = [(entity, prop) for entity in entities for prop in props]
    ref_keys = [prop.get_value_for_datastore(x) for x, prop in fields]
    fetch_keys = set(filter(None, ref_keys))  # Only fetch non-null keys
    if fetch_keys:
      ref_entities = dict((x.key(), x) for x in db.get(fetch_keys))
      for (entity, prop), ref_key in zip(fields, ref_keys):
          prop.__set__(entity, ref_entities.get(ref_key, None))
    return entities


map_dict_entries = [
    'float_num',
    'name',
    'description',
    'mapdata',
    'rating',
    'votes',
    'disableratings',
    'unlisted',
    'comment_count',
    'featured_text',
]
map_dict_date_entries = [
    'lastupdated',
    'created',
    'featured_date',
]


def build_map_dict(map):
  map_dict = dict((k, getattr(map, k)) for k in map_dict_entries)
  map_dict.update((k, isodate(getattr(map, k))) for k in map_dict_date_entries)
  map_dict['user'] = map.user.username
  map_dict['featured_by'] = map.featured_by.username if map.featured_by else None
  map_dict['tags'] = list(map.tags)
  map_dict['map_id'] = map.map_id
  map_dict['image_url'] = map.image_url
  return map_dict


comment_dict_entries = [
    'title',
    'text',
    'demodata',
]


def build_comment_dict(comment):
  comment_dict = dict((k, getattr(comment, k)) for k in comment_dict_entries)
  comment_dict['map_id'] = int(comment.key().parent().name()[1:])
  comment_dict['comment_id'] = comment.key().id()
  comment_dict['lastupdated'] = isodate(comment.lastupdated)
  comment_dict['author'] = comment.author.username
  return comment_dict

class MapDataHandler(lib.BaseHandler):
  def get(self, request, map_id):
    map = model.Map.get_by_map_id(int(map_id))
    data = build_map_dict(map)
    return HttpResponse(
      simplejson.dumps(data),
      content_type="text/json"
    )


class CommentDataHandler(lib.BaseHandler):
  def get(self, request, map_id):
    q = model.Comment.all().ancestor(model.Map.get_key(int(map_id))).fetch(1000)
    data = [build_comment_dict(c) for c in q]
    return HttpResponse(
      simplejson.dumps(data),
      content_type="text/json"
    )


class MapFirehoseHandler(lib.BaseHandler):
  def get(self, request):
    count = int(self.request.GET.get('count', 100))
    start = self.request.GET.get('start', None)
    tags = self.request.GET.getlist('tag')
    
    q = model.Map.all()
    if tags:
      for tag in tags:
        q.filter("tags =", tag)
      q.filter("unlisted =", False)
      q.order('-float_num')
    else:
      q.order('lastupdated')
    if start:
      q.with_cursor(start)
    maps = q.fetch(count)
    prefetch_refprops(maps, model.Map.user, model.Map.featured_by)
    data = {
        'data': [build_map_dict(map) for map in maps],
        'count': len(maps),
        'next': q.cursor().decode(),
    }
    return HttpResponse(
      simplejson.dumps(data),
      content_type="text/json"
    )

class CommentFirehoseHandler(lib.BaseHandler):
  def get(self, request):
    count = int(self.request.GET.get('count', 100))
    start = self.request.GET.get('start', None)
    q = model.Comment.all().order('lastupdated')
    if start:
      q.with_cursor(start)
    comments = q.fetch(count)
    prefetch_refprops(comments, model.Comment.author)
    data = {
        'data': [build_comment_dict(comment) for comment in comments],
        'count': len(comments),
        'next': q.cursor().decode(),
    }

    return HttpResponse(
      simplejson.dumps(data),
      content_type="text/json"
    )

