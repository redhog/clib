import django.contrib.auth.models
import fcdjangoutils.jsonview
import django.contrib.sites.models
import django.core.urlresolvers
import django.shortcuts
import hashlib
from django.conf import settings
import django.views.decorators.csrf
import django.contrib.auth.decorators
import appomatic_clib.models
import appomatic_renderable.models
import qrcode
import qrcode.image.svg
import StringIO

def login_user(request, user):
    "Log in a user without requiring credentials"
    from django.contrib.auth import load_backend, login
    if not hasattr(user, 'backend'):
        for backend in settings.AUTHENTICATION_BACKENDS:
            if user == load_backend(backend).get_user(user.pk):
                user.backend = backend
                break
    if hasattr(user, 'backend'):
        return login(request, user)

def relogin(str):
    username, hash = str.split(":")
    if hash != hashlib.sha1(settings.CLIB_SECRET + username).hexdigest():
        raise Exception("Bad user id signature")
    return django.contrib.auth.models.User.objects.get(username=username)

@django.views.decorators.csrf.csrf_exempt
@fcdjangoutils.jsonview.json_view
def scan_start(request, user):
    login_user(request, relogin(user))
    print "START SCAN:", request.user.username
    return {
        "name": "CommonLibrary",
        "url": 'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse(scan_item, kwargs={"user":user}),
        "type": "get",
        "text": "Please scan the ISBN labels of any books to add or the QR code of any books to check in/out."
        }

@django.views.decorators.csrf.csrf_exempt
@fcdjangoutils.jsonview.json_view
def scan_item(request, user):
    login_user(request, relogin(user))

    print "SCAN:", request.user.username, request.GET['data'], request.GET['type']

    if request.GET['type'] == 'QR_CODE':
        t = appomatic_clib.models.Object.objects.get(id=request.GET['data'].split('/')[-1]).subclassobject

        if isinstance(t, appomatic_clib.models.Thing):
            profile = request.user.profile
            profile.current_thing = t
            profile.save()
            
            if t.holder.id == request.user.id:
                return {"text": "Current book: %s" % (t,)}
            #     if t.request:
            #         t.request.send()
            #     else:
            #         raise Exception("Hm, why'd you scan this one now?")
            elif t.request and t.request.requestor.id == request.user.id:
                t.request.receive()
                return {text: "Received %s" % (t,)}
            else:
                return {"text": "How on earth did this user get the QR-code??"}
        elif isinstance(t, appomatic_clib.models.Shelf):
            thing = request.user.profile.current_thing
            if thing:
                thing.shelf = t
                thing.save()
                return {"text": "%s set on shelf %s" % (thing, t)}
    else:
        data = dict(request.GET.iteritems())
        data['barcode_type'] = data.pop('type')
        data['barcode_data'] = data.pop('data')
        tt = appomatic_clib.models.ThingType.get(**data)
        t = appomatic_clib.models.Thing(type=tt, owner=request.user, holder=request.user)
        t.save()
        return {"text": "Added %s" % (t,)}

    return {}
