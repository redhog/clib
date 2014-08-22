INSTALLED_APPS += [
    "qrcode",
    "userena",
    "guardian",
    "easy_thumbnails",
    "django.contrib.gis",
    "django.contrib.messages"
]

MIDDLEWARE_CLASSES = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "fcdjangoutils.middleware.GlobalRequestMiddleware"
]

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.messages.context_processors.messages"
]
