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

def start_url(request):
    return 'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse('appomatic_clib.views.scan.scan_start', kwargs={"user":sign_login(request)})

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
            "tags": appomatic_renderable.models.Tag.objects.filter(parent=None),
            "latest_additions": appomatic_clib.models.ThingType.objects.order_by('-added'),
            "request": request
        }
    )

@django.contrib.auth.decorators.login_required
def add(request):
    if request.method == 'POST':
        type = request.POST['type']
        if type == "none":
            tt = appomatic_clib.models.ThingType(name = request.POST['name'])
            tt.save()
            t = appomatic_clib.models.Thing(type=tt, owner=request.user, holder=request.user)
            t.save()
            return django.shortcuts.redirect(
                tt.get_absolute_url() + "?" + tt.fieldname + "method=edit")
        else:
            res = []
            for code in request.POST['codes'].split(" "):
                data = {
                    'barcode_type': type,
                    'barcode_data': code
                    }
                tt = appomatic_clib.models.ThingType.get(**data)
                t = appomatic_clib.models.Thing(type=tt, owner=request.user, holder=request.user)
                t.save()
                res.append(t)
            if len(res) == 1:
                return django.shortcuts.redirect(res[0].get_absolute_url())
            else:
                django.contrib.messages.add_message(
                    request, django.contrib.messages.INFO,
                    '<div>Added multiple things:</div>%s' % ''.join("<div>%s</div>" % item.render(style='link__html') for item in res))

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
        for thing in request.user.profile.things_needs_labels.all():
            thing.label_printed = True
            thing.save()
        for shelf in request.user.profile.shelfs_needs_labels.all():
            shelf.label_printed = True
            shelf.save()
        return django.shortcuts.redirect('appomatic_clib.views.index')
        
    return django.shortcuts.render(
        request,
        'appomatic_clib/labels.html',
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

@django.contrib.auth.decorators.login_required
def shelfs(request):
    if request.method == 'POST':
        action = request.POST['action']
        if action == "add":
            appomatic_clib.models.Shelf(
                name = request.POST['name'],
                owner = request.user).save()
        elif action == "delete":
            shelf = appomatic_clib.models.Shelf.objects.get(id=request.POST['id'])
            for thing in shelf.contains.all():
                thing.shelf = None
                thing.save()
            shelf.delete()
    return django.shortcuts.render(
        request,
        'appomatic_clib/shelfs.html',
        {
            "request": request
        }
    )

@django.contrib.auth.decorators.login_required
def messages(request):
    return django.shortcuts.render(
        request,
        'appomatic_clib/messages.html',
        {
            "request": request
        }
    )

def render_qr(request):
    url = request.GET['url']
    print url
    
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, image_factory=qrcode.image.svg.SvgImage)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    stream = StringIO.StringIO()
    img.save(stream)

    return django.http.HttpResponse(stream.getvalue(), content_type="image/svg+xml")
