from django.urls import path

from . import views
from .my_view import RequestSettings, Method

urlpatterns = [
    path('search/', RequestSettings(method=Method.POST, func_to_call=views.search)),
    path('favorite_list/', RequestSettings(method=Method.GET, func_to_call=views.favorite_list)),
    path('change_video_favorite_status/', RequestSettings(method=Method.POST, func_to_call=views.change_video_favorite_status))
]