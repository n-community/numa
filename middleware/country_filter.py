from django.http import HttpResponseForbidden

class CountryFilter:
  def __init__(self, get_response):
    self.get_response = get_response


  def __call__(self, request):
    country = request.headers.get("X-Appengine-Country")
    if country in ("CN", "HK"):
      return HttpResponseForbidden()

    response = self.get_response(request)
    return response
