INSTALLED_APPS += [
    "mptt",
    "userena",
    "guardian",
    "easy_thumbnails",
    "django.contrib.gis",
    "django.contrib.messages",
    "endless_pagination",
    "fcdjangoutils"
]

MIDDLEWARE_CLASSES = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "fcdjangoutils.middleware.EarlyResponse",
    "fcdjangoutils.middleware.GlobalRequestMiddleware",
    "fcdjangoutils.widgettagmiddleware.WidgetTagMiddleware"
]

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request'
]

PRE = ["appomatic_admin", "appomatic_djangoobjfeed"]
POST = ["appomatic_renderable"]
