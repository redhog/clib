import django.conf.urls
import django.views.generic

urlpatterns = django.conf.urls.patterns('',
    django.conf.urls.url(r'^/?$', 'appomatic_clib.views.index'),

    django.conf.urls.url(r'^search/?$', 'appomatic_clib.views.search'),
    django.conf.urls.url(r'^search/thing/?$', 'appomatic_clib.views.search_thing'),

    django.conf.urls.url(r'^add/?$', 'appomatic_clib.views.add'),
    django.conf.urls.url(r'^labels/?$', 'appomatic_clib.views.labels'),
    django.conf.urls.url(r'^owns/?$', 'appomatic_clib.views.owns'),
    django.conf.urls.url(r'^has/?$', 'appomatic_clib.views.has'),
    django.conf.urls.url(r'^shelfs/?$', 'appomatic_clib.views.shelfs'),
    django.conf.urls.url(r'^shelfs/none/?$', 'appomatic_clib.views.shelf_no_shelf'),
    django.conf.urls.url(r'^messages/?$', 'appomatic_clib.views.messages'),

    django.conf.urls.url(r'^funds/add/paypal/return/?$', 'appomatic_clib.views_funds.paypal_add_return'),
    django.conf.urls.url(r'^funds/?$', 'appomatic_clib.views_funds.funds'),

    django.conf.urls.url(r'^(?P<user>.*)/scan/start/?$', 'appomatic_clib.views.scan_start'),
    django.conf.urls.url(r'^(?P<user>.*)/scan/item/?$', 'appomatic_clib.views.scan_item'),

    django.conf.urls.url(r'^accounts/(?P<username>.*)/edit/?$', 'appomatic_clib.views_profile.edit'),
    django.conf.urls.url(r'^accounts/', django.conf.urls.include('userena.urls')),

    django.conf.urls.url(r'^tag(?P<url>.*)/?$', 'appomatic_renderable.views.tag'),

    django.conf.urls.url(r'^qr/?$', 'appomatic_clib.views.render_qr'),

    django.conf.urls.url(r'^(?P<id>.*)/?$', 'appomatic_clib.views.get'),

)
