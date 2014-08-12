import appomatic_clib.models
import django.contrib.admin

django.contrib.admin.site.register(appomatic_clib.models.ThingType)
django.contrib.admin.site.register(appomatic_clib.models.Thing)
django.contrib.admin.site.register(appomatic_clib.models.LendingRequest)
