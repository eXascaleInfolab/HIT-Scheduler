from django.conf.urls import patterns, url, include
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'train.views.work', name='work'),
    url(r'^batch/(?P<task_id>\d+)/$', 'train.views.work', name='work'),
    url(r'^submit/(?P<task_id>\d+)/$', 'train.views.submit', name='submit'),
    url(r'^accounts/',  include('accounts.urls')),
    url(r'^welcome$', 'train.views.welcome', name='welcome'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

if True or not settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT}),
    )
