import os
# specify the name of your settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'myapp.settings'

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import datastore
from beaker.middleware import SessionMiddleware

from controllers import *

application = webapp.WSGIApplication([
    ("/(news.atom)?", HomePage),
    ("/about", AboutPage),
    ("/faq", FAQPage),
    ("/other", OtherPage),
    ("/sundayn(?:/([0-9]+))?(?:/([^/]+))?", SundayNPage),
    ("/browse(.rss)?", BrowsePage),
    ("/(userlevels)", BrowsePage),
    ("/search", AdvancedSearchPage),
    ("/unread", UnreadPage),
    ("/featured(.atom)?", FeaturedPage),
    ("/authors", AuthorActivityPage),
    ("/submit", SubmitPage),
    ("/login", LoginPage),
    ("/logout", LogoutPage),
    ("/verify", VerifyPage),
    ("/user(?:/([^/]+)(?:/([^/]+))?)?", UserInfoPage),
    ("/whoswho", WhosWhoPage),
    ("/suggest_tags", SuggestTagsPage),
    ("/admin/modqueue", ModerationQueuePage),
    ("/admin/newspost", NewsPostPage),
    ("/map/([0-9]+)(?:/([^/]+))?", MapRedirectPage),
    ("/([0-9]+)/mapdata", MapDataHandler),
    ("/([0-9]+)/commentdata", CommentDataHandler),
    ("/([0-9]+)(?:/([^/]+))?", MapPage),
    ("/api/maps", MapFirehoseHandler),
    ("/api/comments", CommentFirehoseHandler),
    ("/preview", PreviewPage)
])


def www_redirect(wsgi_app):
  def do_www_redirect(env, start_response):
    if env["HTTP_HOST"] == "nmaps.net":
      newurl = "http://www.nmaps.net%s%s" % (env["SCRIPT_NAME"],
                                             env["PATH_INFO"])
      query_str = env.get("QUERY_STRING", "")
      if query_str:
        newurl += "?%s" % query_str

      start_response("301 Moved Permanently", [("Location", newurl)])
      return ["<html><head><title>301 Moved Peramanently</title></head>",
              "<body><a href=\"%s\">Click Here</a></body></html>" % newurl]
    else:
      return wsgi_app(env, start_response)

  return do_www_redirect


application = SessionMiddleware(application, type="google", table_name="Session",
                                cookie_expires=False)
application = www_redirect(application)

def main():
  util.run_wsgi_app(application)

if __name__ == "__main__":
  main()
