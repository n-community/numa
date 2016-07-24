import lib

class AboutPage(lib.BaseHandler):
  template_names = {
    "get": "about.html",
  }

class FAQPage(lib.BaseHandler):
  template_names = {
    "get": "faq.html",
  }
