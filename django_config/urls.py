"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# from django.contrib import admin
from django.urls import path, re_path

from controllers.about      import AboutPage, FAQPage
from controllers.api        import MapDataHandler, CommentDataHandler, MapFirehoseHandler, CommentFirehoseHandler
from controllers.admin      import ModerationQueuePage, NewsPostPage
from controllers.auth       import LoginPage, LogoutPage, VerifyPage
from controllers.featured   import FeaturedPage
from controllers.home       import HomePage
from controllers.map        import MapPage, MapRedirectPage, PreviewPage, SubmitPage
from controllers.other      import OtherPage
from controllers.query      import AdvancedSearchPage, BrowsePage, UnreadPage
from controllers.sundayn    import SundayNPage
from controllers.tags       import SuggestTagsPage
from controllers.user       import UserInfoPage, AuthorActivityPage, WhosWhoPage

# from controllers.seed import SeedPage


urlpatterns = [
    # path('admin/', admin.site.urls), # django thingy
    # path("seed", SeedPage.as_view()), # seed DBs (wip)

    re_path(r"^(news.atom)?$", HomePage.as_view()),
    path("about", AboutPage.as_view()),
    path("faq", FAQPage.as_view()),
    path("other", OtherPage.as_view()),
    re_path(r"^sundayn(?:/([0-9]+))?(?:/([^/]+))?", SundayNPage.as_view()),
    re_path(r"^browse(.rss)?", BrowsePage.as_view()),
    re_path(r"^(userlevels)", BrowsePage.as_view()),
    path("search", AdvancedSearchPage.as_view()),
    path("unread", UnreadPage.as_view()),
    re_path(r"^featured(.atom)?", FeaturedPage.as_view()),
    path("authors", AuthorActivityPage.as_view()),
    path("submit", SubmitPage.as_view()),
    path("login", LoginPage.as_view()),
    path("logout", LogoutPage.as_view()),
    path("verify", VerifyPage.as_view()),
    re_path(r"^user(?:/([^/]+)(?:/([^/]+))?)?", UserInfoPage.as_view()),
    path("whoswho", WhosWhoPage.as_view()),
    path("suggest_tags", SuggestTagsPage.as_view()),
    path("admin/modqueue", ModerationQueuePage.as_view()),
    path("admin/newspost", NewsPostPage.as_view()),
    re_path(r"^map/([0-9]+)(?:/([^/]+))?", MapRedirectPage.as_view()),
    re_path(r"^([0-9]+)/mapdata", MapDataHandler.as_view()),
    re_path(r"^([0-9]+)/commentdata", CommentDataHandler.as_view()),
    re_path(r"^([0-9]+)(?:/([^/]+))?", MapPage.as_view()),
    path("api/maps", MapFirehoseHandler.as_view()),
    path("api/comments", CommentFirehoseHandler.as_view()),
    path("preview", PreviewPage.as_view()),
]