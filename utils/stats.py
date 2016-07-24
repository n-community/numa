import array
import logging
import mapper
import model

from google.appengine.ext import db

def regenerateUserStats(user):
  user.rating_histogram = array.array("i", [0]*model.User.HISTOGRAM_SIZE)
  user.map_count = 0
  user.rated_map_count = 0
  user.featured_map_count = 0
  user.favourite_count = 0
  
  maps = mapper.KindIterator(model.Map, [('user', user)], batch_size=200)
  for map in maps:
    if map.unlisted:
      continue
    user.map_count += 1
    if map.rated:
      bar = min(int((map.rating / model.Map.MAX_RATING)
                    * model.User.HISTOGRAM_SIZE), model.User.HISTOGRAM_SIZE - 1)
      user.rating_histogram[bar] += 1
      user.rated_map_count += 1
    if map.featured_date:
      user.featured_map_count += 1
  
  favs = mapper.KindIterator(model.Favorite, ancestor=user, batch_size=500)
  for fav in favs:
    user.favourite_count += 1
  
  print "Updating user %s" % (user.username,)
  while True:
    try:
      user.put()
      break
    except db.Timeout:
      pass


def regenerateAllUsers():
  for user in mapper.KindIterator(model.User, batch_size=10):
    regenerateUserStats(user)

def regenerateMapTags(map, user_map):
  user = user_map[map._user]
  author_tag = u"author:%s" % (user.username,)
  norm_author_tag = model.Tag.normalise(author_tag)
  updated = False
  map.tags.discard(author_tag)
  if norm_author_tag not in map.tags:
    map.tags.add(norm_author_tag)
    updated = True
  if map.rated and u"rated" not in map.tags:
    map.tags.add(u"rated")
    updated = True
  elif not map.rated and u"unrated" not in map.tags:
    map.tags.add(u"unrated")
    updated = True
  return updated

def regenerateAllMaps():
  updater = mapper.BatchUpdater()
  user_map = dict((x.key(), x) for x in mapper.KindIterator(model.User))
  all_tags = {}
  for map in mapper.KindIterator(model.Map):
    if regenerateMapTags(map, user_map):
      updater.add(map)
    for tag in map.tags:
      all_tags[tag] = all_tags.get(tag, 0) + 1
  logging.info("Writing updated tags")
  del all_tags[""]
  del all_tags["rated"]
  del all_tags["unrated"]
  tags = [model.Tag(key_name=model.Tag.get_key_name(tag), name=tag, count=count)
          for tag, count in all_tags.iteritems()]
  updater.add(tags)
  updater.flush()
  return all_tags.keys()
