# -*- coding: utf-8 -*-:
from django.conf.urls import patterns, url

import views

urlpatterns = patterns('',
    url(r'^logout/$', views.logout_view, name="logout_view"),
    url(r'^login/$', views.login_view, name="login_view"),
)
