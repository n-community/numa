import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_config.settings')


from google.appengine.api import datastore
from google.appengine.api import wrap_wsgi_app # new

from django_config.wsgi import application as app

app = wrap_wsgi_app(app) # new

# def main():
#   util.run_wsgi_app(app)

# if __name__ == "__main__":
#   main()
