import django.db.models
import django.contrib.gis.db.models
import django.contrib.auth.models
import appomatic_clib.isbnlookup
import django.db.models
import fcdjangoutils.middleware
import appomatic_renderable.models
import fcdjangoutils.fields
from django.conf import settings
import urllib
from . import base
from . import transactions
from . import events


class Shelf(base.Object):
    class Meta:
        app_label = 'appomatic_clib'
        ordering = ('name', )

    name = django.db.models.CharField(default='', blank=True, max_length=512, db_index=True)
    owner = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="shelfs")
    label_printed = django.db.models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

class ThingType(base.Object):
    barcode_type = django.db.models.CharField(max_length=128, blank=True, db_index=True)
    barcode_data = django.db.models.CharField(max_length=512, blank=True, db_index=True)
    name = django.db.models.CharField(default='', blank=True, max_length=256, db_index=True)
    producer = django.db.models.CharField(default='', blank=True, max_length=256, db_index=True)
    designer = django.db.models.CharField(default='', blank=True, max_length=256, db_index=True)
    description = django.db.models.TextField(default='', blank=True)
    log = fcdjangoutils.fields.JsonField(default=[], null=True, blank=True)

    tags = django.db.models.ManyToManyField(appomatic_renderable.models.Tag, null=True, blank=True, related_name='things')

    added = django.db.models.DateTimeField(auto_now_add=True, null=True, blank=True)

    do_lookup = False

    class Meta:
        app_label = 'appomatic_clib'
        ordering = ('name', )

    def save(self, *arg, **kw):
        self.log = self.log + [{
            "barcode_type": self.barcode_type,
            "barcode_data": self.barcode_data,
            "name": self.name,
            "producer": self.producer,
            "designer": self.designer,
            "description": self.description 
            }]
        if self.barcode_type == 'EAN_13' and ((self.name == '' and self.designer == '') or self.do_lookup):
            res = appomatic_clib.isbnlookup.ISBNLookup.lookup(self.barcode_data)
            if res is not None:
                self.designer, self.name = res
        base.Object.save(self, *arg, **kw)

    @classmethod
    def get(cls, barcode_type, barcode_data, **kw):
        existing = cls.objects.filter(barcode_type=barcode_type, barcode_data=barcode_data)
        if existing:
            return existing[0]
        tt = cls(barcode_type=barcode_type, barcode_data=barcode_data, **kw)
        tt.save()
        return tt

    def available_of_this_type(self):
        res = Thing.geoobjects.filter(type=self, available=True)
        request = fcdjangoutils.middleware.get_request()

        if not request.user.is_authenticated() or not request.user.profile:
            return res
        user = request.user.profile.location
        if not user or not user.position:
            return res

        return res.distance(user.position, field_name='location__position').order_by('distance')

    @property
    def price(self):
        return self.of_this_type.aggregate(django.db.models.Avg('price'))['price__avg']

    def __unicode__(self):
        return u"%(name)s: %(barcode_type)s/%(barcode_data)s" % {"name": self.name, "barcode_type": self.barcode_type, "barcode_data": self.barcode_data}

    def handle__lookup(self, request, style):
        self.do_lookup = True
        self.save()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self))

    def handle__save(self, request, style):
        form = ThingTypeForm(request.POST, instance=self)
        if form.is_valid():
            form.save()
            raise fcdjangoutils.responseutils.EarlyResponseException(
                django.shortcuts.redirect(self))
        return {"form": form}

    def handle__add(self, request, style):
        thing = Thing(type=self, owner=request.user)
        thing.save()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(thing))

    def handle__edit(self, request, style):
        form = ThingTypeForm(instance=self)
        return {"form": form}

    def oembed(self, request, context):
        res = base.Object.oembed(self, request, context)
        res['title'] = self.name
        res['author_name'] = self.designer
        return res


class ThingTypeForm(django.forms.ModelForm):
    class Meta:
        app_label = 'appomatic_clib'
        model = ThingType
        fields = ['name', 'producer', 'designer', 'description']
    tags = django.forms.CharField(widget=django.forms.Textarea(attrs={'rows': 4}), label="Tags", required = False)

    def __init__(self, *arg, **kw):
        if 'instance' in kw:
            if 'initial' not in kw: kw['initial'] = {}
            kw['initial']['tags'] = '\n'.join(
                tag.path
                for tag in kw['instance'].tags.all())
        super(ThingTypeForm, self).__init__(*arg, **kw)

    def save(self, commit=True):
        res = super(ThingTypeForm, self).save(commit=commit)
        res.tags.clear()
        for tag in self.cleaned_data['tags'].replace("\r", "").replace(",", "\n").split("\n"):
            if not tag: continue
            tag_model = None
            for item in tag.split("/"):
                existing = appomatic_renderable.models.Tag.objects.filter(parent=tag_model, name=item)
                if existing:
                    tag_model = existing[0]
                else:
                    tag_model = appomatic_renderable.models.Tag(parent=tag_model, name=item)
                    tag_model.save()
            res.tags.add(tag_model)
        return res

class Thing(base.Object):
    objects = django.db.models.Manager()
    geoobjects = django.contrib.gis.db.models.GeoManager()

    type = django.db.models.ForeignKey(ThingType, related_name='of_this_type')

    owner = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="owns")
    holder = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="has")

    label_printed = django.db.models.BooleanField(default=False)

    lent_until = django.db.models.DateTimeField(null=True, blank=True)
    deposit_payed =  django.db.models.ForeignKey(transactions.Transaction, null=True, blank=True)
    price = django.db.models.FloatField(default=100.0)

    available = django.db.models.BooleanField(default=True)

    location = django.db.models.ForeignKey("Location", related_name="held_here", null=True, blank=True)
    shelf = django.db.models.ForeignKey("Shelf", related_name="contains", null=True, blank=True)

    added = django.db.models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        app_label = 'appomatic_clib'
        ordering = ('type__name', )

    def distance(self):
        request = fcdjangoutils.middleware.get_request()
        if hasattr(request.user, 'profile'):
            user = request.user.profile.location
            if user and user.position:
                return Thing.geoobjects.filter(id=self.id).distance(user.position, field_name='location__position')[0].distance
        return '-'

    @property
    def request(self):
        if not self.requests.count():
            return None
        return self.requests.order_by('time')[0]

    def lose(self):
        events.Lost(
            thing = self,
            affected = self.request and self.request.requestor,
            old_owner = self.owner,
            new_owner = self.holder).save()

        self.available = False
        self.owner = self.holder
        if self.deposit_payed:
            deposit_payed = self.deposit_payed
            deposit_payed.tentative = False
            deposit_payed.pending = False
            deposit_payed.save()
        self.save()
        
        for request in self.requests.all():
            request.cancel()

    def set_price(self, amount):
        self.price = amount
        self.save()

    def save(self, *arg, **kw):
        try:
            holder = self.holder
        except:
            self.holder = self.owner
        try:
            self.location = self.holder.profile.location
        except:
            pass
        base.Object.save(self, *arg, **kw)

    def __unicode__(self):
        return u"%(type)s: %(id)s owned by %(owner)s" % {"type": self.type, "id": self.id, "owner": self.owner}

    def handle__request(self, request, style):
        assert self.holder.id != request.user.id
        lr = appomatic_clib.models.LendingRequest(thing=self, requestor=request.user)
        lr.save()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(lr))

    def handle__lose(self, request, style):
        assert request.user.id == self.holder.id
        self.lose()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self))

    def handle__make_available(self, request, style):
        assert request.user.id == self.holder.id
        self.available = True
        self.save()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self))

    def handle__set_price(self, request, style):
        assert request.user.id == self.owner.id
        self.set_price(request.POST['amount'])
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self))

    def handle__set_shelf(self, request, style):
        assert request.user.id == self.holder.id
        if request.POST['shelf']:
            self.shelf = Shelf.objects.get(id=request.POST['shelf'])
        else:
            self.shelf = None
        self.save()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self))

    def oembed(self, request, context):
        res = base.Object.oembed(self, request, context)
        res['title'] = self.type.name
        res['author_name'] = self.type.designer
        return res

@property
def path(self):
    return "/".join(
        item.name
        for item in self.get_ancestors(include_self=True))
appomatic_renderable.models.Tag.path = path

def tag_get_absolute_url(self):
    return django.core.urlresolvers.reverse('appomatic_clib.views.search.search') + "?tags=" + urllib.quote_plus(self.path)
appomatic_renderable.models.Tag.get_absolute_url = tag_get_absolute_url
