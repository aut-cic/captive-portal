from django.urls import path

from . import views

urlpatterns = [
    path(r"info/", views.index),
    path(r"userusage/", views.user_usage),
    path(r"logout/", views.logout),
]
