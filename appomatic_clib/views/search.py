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

def get_tag_by_path(path, create = False):
    tag_model = None
    for item in path.split('/'):
        existing = appomatic_renderable.models.Tag.objects.filter(parent=tag_model, name=item)
        if existing:
            tag_model = existing[0]
        else:
            if not create:
                raise Exception("Unknown tag")
            tag_model = appomatic_renderable.models.Tag(parent=tag_model, name=item)
            tag_model.save()
    return tag_model

@django.views.decorators.csrf.csrf_exempt
def search(request):
    query = dict(
        text = "",
        tags = [],
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
    
    if 'update-text' in query:
        query['text'] = query['update-text']

    if 'update-tags' in query:
        tag = query['update-tags']
        if tag in query['tags']:
            query['tags'].remove(tag)
        else:
            query['tags'].append(tag)

    query_string = django.http.QueryDict("", mutable=True)
    for key, value in query.iteritems():
        if not key.startswith("update-"):
            if key == 'tags':
                query_string.setlist(key, value)
            else:
                query_string[key] = value
    query_string = query_string.urlencode()

    results = appomatic_clib.models.ThingType.objects.all()

    info_objects = []

    text = query.get('text', None)
    if text:
        results = results.filter(
            django.db.models.Q(name__icontains=text)
            | django.db.models.Q(designer__icontains=text)
            | django.db.models.Q(producer__icontains=text)
            | django.db.models.Q(description__icontains=text)
            | django.db.models.Q(barcode_data__icontains=text))

    for t in query.get('tags'):
        results = results.filter(tags = get_tag_by_path(t))

    results = results.annotate(count=django.db.models.Count('of_this_type'))

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

    if request.user.is_staff:
        if query.get('action', None) == 'add-tag':
            if query.get('action_tag_name', None):
                tag = get_tag_by_path(query['action_tag_name'], True)
            else:
                tag = get_tag_by_path(query['action_tag'])
            for thing_type in results:
                thing_type.tags.add(tag)

        if query.get('action', None) == 'remove-tag':
            tag = get_tag_by_path(query['action_tag'])
            for thing_type in results:
                thing_type.tags.remove(tag)

        if query.get('action', None) == 'del-tag':
            get_tag_by_path(query['action_tag']).delete()

    return django.shortcuts.render(
        request,
        'appomatic_clib/search.html',
        {
            "query_string": request.path + "?" + query_string,
            "query": query,
            "tags": appomatic_renderable.models.Tag.objects.all(),
            "sort_icons": sort_icons,
            "results": results,
            "info_objects": info_objects,
            "request": request
        }
    )


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
    
    if 'update-text' in query:
        query['text'] = query['update-text']

    if 'update-tags' in query:
        tag = query['update-tags']
        if tag in query['tags']:
            query['tags'].remove(tag)
        else:
            query['tags'].append(tag)

    if 'update-shelf' in query:
        query['shelf'] = query['update-shelf']

    query_string = django.http.QueryDict("", mutable=True)
    for key, value in query.iteritems():
        if not key.startswith("update-"):
            if key == 'tags':
                query_string.setlist(key, value)
            else:
                query_string[key] = value
    query_string = query_string.urlencode()

    results = appomatic_clib.models.Thing.geoobjects.all()

    info_objects = []

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
            info_objects.append(shelf)
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

    results = results.distance(request.user.profile.location.position, field_name='location__position')

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
            "query_string": request.path + "?" + query_string,
            "query": query,
            "tags": appomatic_renderable.models.Tag.objects.all(),
            "shelfs": request.user.shelfs.all(),
            "sort_icons": sort_icons,
            "results": results,
            "info_objects": info_objects,
            "request": request
        }
    )
