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
            "tags": appomatic_renderable.models.Tag.objects.filter(parent=None),
            "latest_additions": appomatic_clib.models.ThingType.objects.order_by('-added'),
            "request": request
        }
    )

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

@django.views.decorators.csrf.csrf_exempt
def search(request):
    get = request.GET

    results = appomatic_clib.models.ThingType.objects

    if 'query' in get:
        q = get['query']
        results = results.filter(
            django.db.models.Q(name__icontains=q)
            | django.db.models.Q(designer__icontains=q)
            | django.db.models.Q(producer__icontains=q)
            | django.db.models.Q(description__icontains=q)
            | django.db.models.Q(barcode_data__icontains=q))

    return django.shortcuts.render(
        request,
        'appomatic_clib/search.html',
        {
            "query": q,
            "results": results,
            "request": request
        }
    )

def get_tag_by_path(path):
    tag_model = None
    for item in path.split('/'):
        tag_model = appomatic_renderable.models.Tag.objects.filter(parent=tag_model, name=item)[0]
    return tag_model

@django.views.decorators.csrf.csrf_exempt
def search_thing(request):
    query = dict(
        text = "",
        tags = [],
        shelf = "",
        has = "",
        owns = "",
        sort = ""
        )
    for key, value in request.GET.iteritems():
        query[key] = value
    query['tags'] = request.GET.getlist('tags')

    if 'update-sort' in query:
        sort = []
        if query['sort']: sort = query['sort'].split(",")
        col = query['update-sort']
        if sort and sort[0] == col:
            sort[0] = "-" + col
        elif sort and sort[0] == "-" + col:
            sort[0] = col
        else:
            if col in sort:
                sort.remove(col)
            if "-" + col in sort:
                sort.remove("-" + col)
            sort[0:0] = [col]
        query['sort'] = ",".join(sort)
    

    if 'update-tags' in query:
        tag = query['update-tags']
        if tag in query['tags']:
            query['tags'].remove(tag)
        else:
            query['tags'].append(tag)

    results = appomatic_clib.models.Thing.geoobjects.all()

    results = results.distance(request.user.profile.location.position, field_name='location__position')

    text = query.get('text', None)
    if text:
        results = results.filter(
            django.db.models.Q(type__name__icontains=text)
            | django.db.models.Q(type__designer__icontains=text)
            | django.db.models.Q(type__producer__icontains=text)
            | django.db.models.Q(type__description__icontains=text)
            | django.db.models.Q(type__barcode_data__icontains=text))

    for t in query.get('tags'):
        results = results.filter(type__tags = get_tag_by_path(t))

    shelf = query.get('shelf', None)
    if shelf:
        if shelf == "none":
            results = results.filter(
                shelf = None)
        else:
            shelf = request.user.shelfs.get(name = shelf)
            results = results.filter(
                shelf = shelf)

    available = query.get('available', None)
    if available:
        results = results.filter(
                available = available == "true")

    has = query.get('has', None)
    if has:
        q = django.db.models.Q(holder = request.user)
        if has == "true":
            results = results.filter(q)
        else:
            results = results.filter(~q)

    owns = query.get('owns', None)
    if owns:
        q = django.db.models.Q(owner = request.user)
        if owns == "true":
            results = results.filter(q)
        else:
            results = results.filter(~q)

    sort = []
    if query['sort']: sort = query['sort'].split(",")
 
    if sort:
        results = results.order_by(*sort)

    sort_icons = {}
    for col in sort:
        if col.startswith("-"):
            sort_icons[col[1:]] = "<i class='fa fa-arrow-up'></i> "
        else:
            sort_icons[col] = "<i class='fa fa-arrow-down'></i> "
        break

    return django.shortcuts.render(
        request,
        'appomatic_clib/search_thing.html',
        {
            "query": query,
            "tags": appomatic_renderable.models.Tag.objects.all(),
            "shelfs": request.user.shelfs.all(),
            "sort_icons": sort_icons,
            "results": results,
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
def shelf_no_shelf(request):
    return django.shortcuts.render(
        request,
        'appomatic_clib/shelfs_no_shelf.html',
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
