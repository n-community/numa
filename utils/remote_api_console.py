#!/usr/bin/python
import code
import getpass
import logging
import sys
import os

logging.basicConfig(level=logging.INFO)

# base_path = "/Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine"
base_path = "C:\\Users\\Audrey\\AppData\\Local\\Google\\Cloud SDK\\google-cloud-sdk\\platform\\google_appengine"
sys.path.append(base_path)
sys.path.append(base_path + "\\lib\\yaml\\lib") # nick says its necessary
sys.path.append(base_path + "\\lib\\webob")
sys.path.append(base_path + "\\lib\\django")

sys.path.append(base_path + "\\lib")
# sys.path.append(base_path + "\\lib\\third_party")
# sys.path.append(base_path + "\\lib\\third_party\\google_auth_oauthlib")

# sys.path.append(
#     os.path.abspath(
#         os.path.dirname(
#             os.path.realpath(__file__))))

# if 'google' in sys.modules:
#     del sys.modules['google']

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

# def auth_func():
#   return raw_input('Username:'), getpass.getpass('Password:')

# if len(sys.argv) < 2:
#   print("Usage: %s app_id [host]" % (sys.argv[0]))
# app_id = sys.argv[1]
# if len(sys.argv) > 2:
#   host = sys.argv[2]
# else:
#   host = '%s.appspot.com' % app_id

# remote_api_stub.ConfigureRemoteDatastore(app_id, '/remote_api', auth_func, host)

# code.interact('App Engine interactive console for %s' % (app_id,), None, locals())
