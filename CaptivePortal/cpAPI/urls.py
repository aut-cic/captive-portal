from django.conf.urls import url

from . import views

urlpatterns = [
    url(r"^info/$", views.index),
    url(r"^userusage/$", views.user_usage),
    url(r"^logout/$", views.logout),
]
