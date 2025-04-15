from django.http import HttpResponseRedirect

class PrependWWW:
  def __init__(self, get_response):
    self.get_response = get_response


  def __call__(self, request):
    if request.get_host() == "nmaps.net":
      new_url  = "https://www.nmaps.net" + request.get_full_path()
      return HttpResponseRedirect(new_url)
    else:
      response = self.get_response(request)
      return response
