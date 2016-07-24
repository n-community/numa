import logging
from lib import imagegen
from google.appengine.ext.deferred import defer
from google.appengine.api import taskqueue
import model
from controllers import map as map_controller

def regenerate_map_image(start_key, chain=True):
  maps = model.Map.all().filter("__key__ >", start_key).order("__key__")
  for map in maps:
      if map.image_url is None:
          if chain:
              try:
                  defer(regenerate_map_image, map.key(), _name="fix2-%s"%start_key)
              except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError):
                pass
          logging.info("Regenerating image for map %r", map.key())
          map.image_url = map_controller.create_map_blob(map.mapdata)
          map.put()
          break
