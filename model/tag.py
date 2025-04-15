from google.appengine.ext import db
import random
import hashlib

class Tag(db.Model):
  name = db.StringProperty(required=True)
  count = db.IntegerProperty(required=True, default=0)
  reccommend = db.BooleanProperty(required=True, default=True)

  @staticmethod
  def normalise(tag):
    return tag.strip().lower()
  
  @staticmethod
  def get_key_name(tag):
    return "_"+hashlib.sha1(Tag.normalise(tag).encode()).hexdigest()

  @staticmethod
  def get_key(tag):
    return db.Key.from_path("Tag", Tag.get_key_name(tag))

  @staticmethod
  def get_or_insert_tag(tag):
    return Tag.get_or_insert(Tag.get_key_name(tag),
                             name=Tag.normalise(tag))


class TagJoin(db.Model):
  prefix = db.StringProperty(required=True)
  tag = db.StringProperty(required=True)
  count = db.FloatProperty(required=True, default=0.0)

  @staticmethod
  def GetPowerset(tags):
    tags = sorted(tags)
    for i in range(1, 2**len(tags)):
      # If there's only 1 tag in this element, skip it
      if not i&(i-1): continue
      s = tuple(tags[j] for j in range(len(tags)) if (1<<j)&i)
      for i in range(len(s)):
        yield s[:i]+s[i+1:]+(s[i],)

  @staticmethod
  def get_key_name(tags):
    return "_" + hashlib.sha1(" ".join([x.strip().lower() for x in tags]).encode()).hexdigest()

  @staticmethod
  def get_key(tags):
    return db.Key.from_path("TagJoin", TagJoin.get_key_name(tags))
  
  @staticmethod
  def get_or_insert_tag_join(tags):
    return TagJoin.get_or_insert(TagJoin.get_key_name(tags),
                                 prefix=" ".join(tags[:-1]),
                                 tag=tags[-1])

  @staticmethod
  def update_joins(added, removed, max_updates):
    join_list = list(added | removed)
    join_keys = [TagJoin.get_key(x) for x in join_list]
    if not join_keys: return
    join_objs = TagJoin.get(join_keys)
    # Create any missing tag joins
    for i in range(len(join_keys)):
      if not join_objs[i]:
        join_objs[i] = TagJoin.get_or_insert(join_keys[i].name(),
                                             prefix=" ".join(join_list[i][:-1]),
                                             tag=join_list[i][-1])

    if len(join_objs) <= max_updates:
      join_probs = [1.0] * len(join_objs)
    else:
      # Calculate update probabilities for each tag join
      join_probs = [1 / (x.count + 1) for x in join_objs]
      join_prob_sum = sum(join_probs)

      # Normalize
      join_probs = [(max_updates / join_prob_sum) * x for x in join_probs]

    # Update each one with the specified probability
    for i in range(len(join_objs)):
      if random.random() < join_probs[i]:
        if join_list[i] in added:
          join_objs[i].count += 1 / join_probs[i]
        else:
          join_objs[i].count -= 1 / join_probs[i]
        join_objs[i].put()
