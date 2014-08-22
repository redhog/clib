import appomatic_clib.models
import django.contrib.admin
import django.contrib.gis.admin

django.contrib.admin.site.register(appomatic_clib.models.Transaction)
django.contrib.admin.site.register(appomatic_clib.models.ThingType)
django.contrib.admin.site.register(appomatic_clib.models.Thing)
django.contrib.admin.site.register(appomatic_clib.models.LendingRequest)
django.contrib.admin.site.register(appomatic_clib.models.Area, django.contrib.gis.admin.OSMGeoAdmin)
