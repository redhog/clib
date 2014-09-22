INSTALLED_APPS += [
    "mptt",
    "qrcode",
    "userena",
    "guardian",
    "easy_thumbnails",
    "django.contrib.gis",
    "django.contrib.messages",
    "endless_pagination"
]

MIDDLEWARE_CLASSES = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "fcdjangoutils.middleware.EarlyResponse",
    "fcdjangoutils.middleware.GlobalRequestMiddleware"
]

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request'
]

PRE = ["appomatic_admin"]
POST = ["appomatic_renderable"]
