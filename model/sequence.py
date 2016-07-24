from google.appengine.ext import db

class Sequence(db.Model):
  number = db.IntegerProperty(required=True, default=1000000)

  @staticmethod
  def GetNextId(seq_name):
    def GetNextIdTxn(seq_key):
      seq = Sequence.get(seq_key)
      id = seq.number
      seq.number += 1
      seq.put()
      return id

    seq = Sequence.get_or_insert(seq_name)
    return db.run_in_transaction(GetNextIdTxn, seq.key())
