import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_config.settings')


from google.appengine.api import datastore
from google.appengine.api import wrap_wsgi_app # new

from django_config.wsgi import application as app

# def www_redirect(wsgi_app):
#   def do_www_redirect(env, start_response):
#     if env["HTTP_HOST"] == "nmaps.net":
#       newurl = "http://www.nmaps.net%s%s" % (env["SCRIPT_NAME"],
#                                              env["PATH_INFO"])
#       query_str = env.get("QUERY_STRING", "")
#       if query_str:
#         newurl += "?%s" % query_str

#       start_response("301 Moved Permanently", [("Location", newurl)])
#       return ["<html><head><title>301 Moved Peramanently</title></head>",
#               "<body><a href=\"%s\">Click Here</a></body></html>" % newurl]
#     else:
#       return wsgi_app(env, start_response)

#   return do_www_redirect



# app = www_redirect(app)
app = wrap_wsgi_app(app) # new

# def main():
#   util.run_wsgi_app(app)

# if __name__ == "__main__":
#   main()
