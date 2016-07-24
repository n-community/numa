import csv
import cStringIO
import imghdr
from google.appengine.api import urlfetch

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key.encode("latin_1"))
        L.append('')
        L.append(str(value))
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"'
                 % (key.encode("latin_1"), filename.encode("latin_1")))
        L.append('Content-Type: image/%s' % imghdr.what(None, value))
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

class ImaginRequest(object):
  def __init__(self, url="http://imagin.notdot.net/do"):
    self.url = url
    self.images = []
    self.instructions = []
  
  def add_image(self, name, filename, data=None):
    if data == None:
      f = open(filename, "r")
      data = f.read()
      f.close()
    self.images.append((name, filename, data))
  
  def op(self, opname, *args):
    self.instructions.append((opname,) + args)
  
  def execute(self):
    instdata = cStringIO.StringIO()
    writer = csv.writer(instdata, delimiter=" ")
    writer.writerows(self.instructions)
    content_type, body = encode_multipart_formdata([("code", instdata.getvalue())], self.images)
    response = urlfetch.fetch(self.url, body, urlfetch.POST, {"Content-Type": content_type})
    return response
