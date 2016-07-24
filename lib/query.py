from google.appengine import runtime
from google.appengine.ext import db

import logging
import random
import hashlib

import model

S_START = 0
S_TAG = 1
S_VALUESTART = 2
S_VALUE = 3
S_QUOTEDVALUE = 4
EOS = -1

MAX_MAPS = 500

class Query(object):
  def __init__(self, query_str, random=False, user=None):
    self._is_contradiction = False
    self._positive_tags = set()
    self._negative_tags = set()
    self._positive_stars = set()
    self._negative_stars = set()
    self._random = random
    self._show_unlisted = False
    self._token_type = None
    self.favorites_processed = 0
    self.maps_processed = 0
    self.query_aborted = False
    self.start_token = None
    self.parsed_query = self.ParseQuery(query_str)
    logging.debug("Parsed query: %r", self.parsed_query)
    self.BuildQueryParts(self.parsed_query)
    self._is_contradiction = not self.BuildQuery(self.parsed_query, user)
    if not random:
      self.query_hash = hashlib.sha1(repr((self.parsed_query, self._show_unlisted))).digest()
  
  def ParseQuery(self, query_str):
    state = S_START
    query = []
    current_tag = ""
    current_value = ""
    positive = True
    
    for char in list(query_str) + [EOS]:
      if state == S_START:
        if char == "-":
          positive = False
        elif char != EOS and not char.isspace():
          current_tag = char
          state = S_TAG
      elif state == S_TAG:
        if char == EOS or char.isspace():
          query.append((current_tag, None, positive))
          state = S_START
          positive = True
        elif char == ":":
          state = S_VALUESTART
        else:
          current_tag += char
      elif state == S_VALUESTART:
        if char == '"':
          state = S_QUOTEDVALUE
          current_value = ""
        elif char == EOS or char.isspace():
          query.append((current_tag, None, positive))
          state = S_START
          positive = True
        else:
          current_value = char
          state = S_VALUE
      elif state == S_VALUE:
        if char == EOS or char.isspace():
          query.append((current_tag, current_value, positive))
          state = S_START
          positive = True
        else:
          current_value += char
      elif state == S_QUOTEDVALUE:
        if char == EOS or char == '"':
          query.append((current_tag, current_value, positive))
          state = S_START
          positive = True
        else:
          current_value += char
    return query

  def BuildQueryParts(self, parsed_query):
    self.query_parts = []
    for tag, value, positive in parsed_query:
      if not positive:
        tag = "-" + tag
      if not value:
        part = tag
      elif " " in value:
        part = "%s:\"%s\"" % (tag, value)
      else:
        part = "%s:%s" % (tag, value)
      self.query_parts.append(model.Tag.normalise(part))
          
  def BuildQuery(self, query, user):
    for tag, value, positive in query:
      tag = tag.lower()
      if tag == "favorites" or tag == "starred":
        if user and not value:
          user_key_name = user.key().name()
        elif value:
          user_key_name = model.User.get_key_name(value)
        else:
          return False
        if positive:
          self._positive_stars.add(user_key_name)
        else:
          self._negative_stars.add(user_key_name)
      elif tag == "delisted":
        if user and ("author", user.username, True) in query:
          self._show_unlisted = True
      else:
        if value:
          tag = u"%s:%s" % (tag, value)
        tag = model.Tag.normalise(tag)
        if positive:
          self._positive_tags.add(tag)
        else:
          self._negative_tags.add(tag)

    logging.debug("+tags: %r, -tags: %r, +favs: %r, -favs: %r",
                  self._positive_tags, self._negative_tags,
                  self._positive_stars, self._negative_stars)

    if self._positive_tags.intersection(self._negative_tags): return False
    if self._positive_stars.intersection(self._negative_stars): return False

    return True

  def ExecuteQuery(self, start_token=None):
    if self._is_contradiction: return
    self.start_token = start_token
    # We can either do a merge join from the users' favorites lists, then
    # fetch the resulting entities and filter on them, or we can query on
    # the entities, then filter on them and possibly check for favorites.
    # We decide which approach to take based on which has the least entries:
    # The rarest tag or the user with the fewest favorites.
    if self._positive_stars:
      # Selecting on favorites
      q = self.ExecuteFavJoin()
    elif not self._positive_stars:
      # _Not_ selecting on favorites
      q = self.ExecuteMapFilter()

    q = self.FilterMaps(q)
    if self._negative_stars:
      logging.debug("Adding FilterFavorites postprocessing step")
      q = self.Group(q, 20, self.FilterFavorites)

    try:
      for map in q:
        if self._token_type == "map_id":
          self.start_token = map.map_id
        elif self._token_type == "float_num":
          self.start_token = map.float_num
        yield map
    except (db.Timeout, runtime.DeadlineExceededError):
      self.query_aborted = True
      return
  
  def ExecuteFavJoin(self):
    logging.debug("Executing query as favorites join")
    self._token_type = "map_id"
    if len(self._positive_stars) == 1:
      q = model.Favorite.all()
      q.ancestor(db.Key.from_path("User", list(self._positive_stars)[0]))
      if self.start_token: q.filter("map_id <", self.start_token)
      q.order("-map_id")
      return self.Group(iter(q), 20, self.FetchMaps)
    else:
      # Merge join on favorite lists
      fav_iters = []
      for x in self._positive_stars:
        star_key = db.Key.from_path("User", x)
        q = model.Favorite.all().ancestor(star_key).order("-map_id")
        if self.start_token: q.filter("map_id <", self.start_token)
        fav_iters.append(iter(q))
      return self.Group(self.MergeJoin(fav_iters), 20, self.FetchMaps)
    
  def ExecuteMapFilter(self):
    logging.debug("Executing query as map filter")
    q = model.Map.all()
    if self._positive_tags:
      for tag in self._positive_tags:
        q.filter("tags =", tag)
      logging.debug("Filtering on tag(s) %r", self._positive_tags)
    q.filter("unlisted =", self._show_unlisted)
    if self._random:
      q.filter("random >", random.random())
      q.order("random")
    else:
      self._token_type = "float_num"
      if self.start_token:
        q.filter("float_num <", self.start_token)
      q.order("-float_num")
    
    return iter(q)

  def FilterMaps(self, maps):
    for map in maps:
      self.maps_processed += 1
      if self.maps_processed >= MAX_MAPS:
        self.query_aborted = True
        return
      if map.tags.intersection(self._negative_tags): continue
      if not map.tags.issuperset(self._positive_tags): continue
      if map.unlisted != self._show_unlisted: continue
      yield map

  def Group(self, q, count, fun, *args, **kwargs):
    maps = []
    try:
      while True:
        for i in range(count):
          maps.append(q.next())
        for x in fun(maps, *args, **kwargs): yield x
        maps = []
    except StopIteration:
      if maps:
        for x in fun(maps, *args, **kwargs): yield x

  def FilterFavorites(self, maps):
    map_keys = set([x.key().name() for x in maps])
    filter_keys = []
    for map_key in map_keys:
      for neg_star in self._negative_stars:
        star_key = db.Key.from_path("User", neg_star)
        filter_keys.append(db.Key.from_path("Favorite", map_key,
                                            parent = star_key))

    self.favorites_processed += len(filter_keys)
    fav_entries = model.Favorite.get(filter_keys)
    user_sets = {}
    for entry in fav_entries:
      if entry is None: continue
      map_key = entry.key().name()
      if entry.key().parent().name() in self._negative_stars:
        map_keys.discard(map_key)

    for map in maps:
      if map.key().name() in map_keys: yield map

  def MergeJoin(self, iters):
    try:
      current = [x.next() for x in iters]
      while True:
        smallest = biggest = 0
        for i in range(len(iters)):
          if current[i].map_id < current[smallest].map_id: smallest = i
          if current[i].map_id > current[biggest].map_id: biggest = i
        if smallest == biggest:
          yield current[smallest]
          current = [x.next() for x in iters]
        else:
          current[biggest] = iters[biggest].next()
    except StopIteration:
      return

  def FetchMaps(self, favs):
    self.favorites_processed += len(favs)
    map_keys = [db.Key.from_path("Map", x.key().name()) for x in favs]
    
    maps = [x for x in model.Map.get(map_keys) if x]
    return maps
