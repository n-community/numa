from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import datastore
from beaker.middleware import SessionMiddleware

class PostEchoHandler(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write("Post stuff here to get it echoed back.")
  
  def post(self):
    self.response.headers['Content-Type'] = self.request.headers['Content-Type']
    self.response.out.write(self.request.body)

application = webapp.WSGIApplication([('/postecho', PostEchoHandler)])

def main():
  util.run_wsgi_app(application)

if __name__ == "__main__":
  main()
