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

def start_url(request):
    return 'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse(scan_start, kwargs={"user":sign_login(request)})

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

def sign_login(request):
    return request.user.username + ":" + hashlib.sha1(settings.CLIB_SECRET + request.user.username).hexdigest()

def relogin(str):
    username, hash = str.split(":")
    if hash != hashlib.sha1(settings.CLIB_SECRET + username).hexdigest():
        raise Exception("Bad user id signature")
    return django.contrib.auth.models.User.objects.get(username=username)

def index(request):
    return django.shortcuts.render(
        request,
        'appomatic_clib/index.html',
        {
            "start_url": start_url(request),
            "request": request
        }
    )

@django.contrib.auth.decorators.login_required
def thing_request(request, id):
    t = appomatic_clib.models.Thing.objects.get(id=id)
    lr = appomatic_clib.models.LendingRequest(thing=t, requestor=request.user)
    lr.save()
    return django.shortcuts.redirect(lr)


@django.contrib.auth.decorators.login_required
def thing_send(request, id):
    t = appomatic_clib.models.Thing.objects.get(id=id)
    assert t.holder.id == request.user.id
    t.request.send()
    return django.shortcuts.redirect(t)

@django.contrib.auth.decorators.login_required
def thing_receive(request, id):
    t = appomatic_clib.models.Thing.objects.get(id=id)
    assert t.request.requestor.id == request.user.id
    t.request.receive()
    return django.shortcuts.redirect(t)

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

    if request.GET['type'] == 'QR_CODE' and '/clib/thing/' in request.GET['data']:
        tid = int(request.GET['data'].split('/clib/thing/')[1].split("/")[0])
        t = appomatic_clib.models.Thing.objects.get(id=tid)

        if t.holder.id == request.user.id:
            if t.request:
                t.request.send()
            else:
                print "Hm, why'd you scan this one now?"
        elif t.request.requestor.id == request.user.id:
            t.request.receive()
        else:
            print "How on earth did this user get the QR-code??"
    else:
        data = dict(request.GET.iteritems())
        data['barcode_type'] = data.pop('type')
        data['barcode_data'] = data.pop('data')
        tt = appomatic_clib.models.ThingType.get(**data)
        t = appomatic_clib.models.Thing(type=tt, owner=request.user, holder=request.user)
        t.save()

    return {}

@django.views.decorators.csrf.csrf_exempt
def search(request):
    q = request.GET['query']
    results = appomatic_clib.models.ThingType.objects.filter(django.db.models.Q(name__icontains=q) | django.db.models.Q(description__icontains=q))

    return django.shortcuts.render(
        request,
        'appomatic_clib/search.html',
        {
            "query": q,
            "results": results,
            "request": request
        }
    )

@django.contrib.auth.decorators.login_required
def add(request):
    if request.method == 'POST':
        type = request.POST['type']
        for code in request.POST['codes'].split(" "):
            data = {
                'barcode_type': type,
                'barcode_data': code
                }
            tt = appomatic_clib.models.ThingType.get(**data)
            t = appomatic_clib.models.Thing(type=tt, owner=request.user, holder=request.user)
            t.save()
    return django.shortcuts.render(
        request,
        'appomatic_clib/add.html',
        {
            "start_url": start_url(request),
            "request": request
        }
    )

@django.contrib.auth.decorators.login_required
def labels(request):
    if request.GET.get('done', None):
        for thing in request.user.needs_labels().all():
            thing.label_printed = True
            thing.save()
        return django.shortcuts.redirect('appomatic_clib.views.index')
        
    return django.shortcuts.render(
        request,
        'appomatic_clib/labels.html',
        {
            "request": request
        }
    )


@django.contrib.auth.decorators.login_required
def owns(request):
    return django.shortcuts.render(
        request,
        'appomatic_clib/owns.html',
        {
            "request": request
        }
    )

@django.contrib.auth.decorators.login_required
def has(request):
    return django.shortcuts.render(
        request,
        'appomatic_clib/has.html',
        {
            "request": request
        }
    )

def get(request, id):
    objs= appomatic_clib.models.Object.objects.filter(id=id)
    if len(objs):
        return objs[0].render(request, as_response = True)
    if id == "" or id == "/":
        return appomatic_clib.models.Object.list_render(request, as_response = True)
    else:
        raise Exception("Unknown id %s" % id)
