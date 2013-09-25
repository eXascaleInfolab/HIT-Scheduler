# -*- coding: utf-8 -*-:
from django.conf.urls import patterns, url

import views

urlpatterns = patterns(
    url(r'^logout$', views.logout_view, name="user-logout"),
    url(r'^login$', views.login_view, name="user-login"),
)
