import django.conf.urls
import django.views.generic

urlpatterns = django.conf.urls.patterns('',
    django.conf.urls.url(r'^clib/?$', 'appomatic_clib.views.index'),
    django.conf.urls.url(r'^clib/thing/(?P<id>.*)/request/?$', 'appomatic_clib.views.thing_request'),
    django.conf.urls.url(r'^clib/thing/(?P<id>.*)/send/?$', 'appomatic_clib.views.thing_send'),
    django.conf.urls.url(r'^clib/thing/(?P<id>.*)/receive/?$', 'appomatic_clib.views.thing_receive'),
    django.conf.urls.url(r'^clib/thing/(?P<id>.*)/?$', 'appomatic_clib.views.thing'),
    django.conf.urls.url(r'^clib/thing-type/(?P<id>.*)/?$', 'appomatic_clib.views.thing_type'),
    django.conf.urls.url(r'^clib/add/?$', 'appomatic_clib.views.add'),
    django.conf.urls.url(r'^clib/search/?$', 'appomatic_clib.views.search'),
    django.conf.urls.url(r'^clib/labels/?$', 'appomatic_clib.views.labels'),
    django.conf.urls.url(r'^clib/(?P<user>.*)/scan/start/?$', 'appomatic_clib.views.scan_start'),
    django.conf.urls.url(r'^clib/(?P<user>.*)/scan/item/?$', 'appomatic_clib.views.scan_item'),
    django.conf.urls.url(r'^accounts/', django.conf.urls.include('userena.urls'))
)
