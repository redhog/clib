INSTALLED_APPS += [
    "qrcode",
    "userena",
    "guardian",
    "easy_thumbnails"
]

MIDDLEWARE_CLASSES = [
    "fcdjangoutils.middleware.GlobalRequestMiddleware"
]
