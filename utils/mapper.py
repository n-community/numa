import logging
import socket
import urllib2
from google.appengine.ext import db

class KindIterator(object):
  def __init__(self, kind, filters=None, ancestor=None, batch_size=100,
               key_field="__key__", start=None):
    self.kind = kind
    if filters:
      self.filters = filters
    else:
      self.filters = []
    self.ancestor = ancestor
    self.batch_size = batch_size
    self.key_field = key_field
    if start:
      self.last_key = start
    else:
      self.last_key = None
    self.current_iter = iter([])
    self.total_fetched = 0
    self.eof = False
  
  def _get_query(self):
    q = self.kind.all();
    for prop, value in self.filters:
      q.filter("%s =" % prop, value)
    if self.ancestor:
      q.ancestor(self.ancestor)
    if self.last_key:
      q.filter("%s >" % self.key_field, self.last_key)
    q.order(self.key_field)
    return q
  
  def __iter__(self):
    return self
  
  def next(self):
    try:
      return self.current_iter.next()
    except StopIteration:
      if self.eof:
        raise StopIteration()
      logging.info("Fetching results %d-%d for kind '%s'", self.total_fetched,
                   self.total_fetched + self.batch_size, self.kind.kind())
      batch_size = self.batch_size
      while True:
        try:
          q = self._get_query()
          results = q.fetch(batch_size)
          break
        except (db.Timeout, urllib2.URLError, socket.error):
          if batch_size > 1:
            batch_size /= 2
          logging.warn("Query timed out; retrying with %d", batch_size)
      if not results:
        raise StopIteration()
      if len(results) < batch_size:
        logging.warn("Reached EOF")
        self.eof = True
      self.total_fetched += len(results)
      if self.key_field == "__key__":
        self.last_key = results[-1].key()
      else:
        self.last_key = results[-1].properties()[self.key_field].__get__(results[-1], None)
      self.current_iter = iter(results)
      return self.current_iter.next()


class BatchUpdater(object):
  def __init__(self, batch_size=100, op=None):
    self.batch_size = batch_size
    if op:
      self.op = op
    else:
      self.op = db.put
    self.current_batch = []
  
  def flush(self, target=0):
    """Reduces the number of unsaved entities to target or fewer."""
    while len(self.current_batch) >= target:
      batch_size = self.batch_size
      while True:
        logging.info("Processing %d of %d entities",
                     min(batch_size, len(self.current_batch)),
                     len(self.current_batch))
        try:
          self.op(self.current_batch[-batch_size:])
          break
        except (db.Timeout, urllib2.URLError, socket.error):
          if batch_size > 1:
            batch_size /= 2
          logging.info("Got timeout while putting batch; retrying with %d", batch_size)
      del self.current_batch[-batch_size:]
      if not self.current_batch:
        return
  
  def add(self, entity):
    if isinstance(entity, list):
      self.current_batch.extend(entity)
    else:
      self.current_batch.append(entity)
    self.flush(self.batch_size)
