import django.db.models
import django.contrib.gis.db.models
import django.contrib.auth.models
import django.core.urlresolvers
import django.contrib.sites.models
import appomatic_clib.isbnlookup
from django.utils.translation import ugettext as _
import userena.models
import django.contrib.auth.models
import django.db.models
import fcdjangoutils.middleware
import uuid
import appomatic_renderable.models
import django.contrib.messages
import fcdjangoutils.fields
import datetime
from django.conf import settings

class Object(django.db.models.Model, appomatic_renderable.models.Renderable):
    id = django.db.models.CharField(max_length=128, blank=True, primary_key=True)

    def save(self, *arg, **kw):
        if not self.id:
            self.id = str(uuid.uuid4())
        django.db.models.Model.save(self, *arg, **kw)

    @fcdjangoutils.modelhelpers.subclassproxy
    def __unicode__(self):
        return self.id

    def get_absolute_url(self):
        return  'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse('appomatic_clib.views.get', kwargs={'id': self.id})

    def comment(self, content, author, recipients=[]):
        Message.post(
            about=self,
            content=content,
            auto = author,
            recipients = recipients)

    def handle__comment(self, request, style):
        self.comment(request.POST['content'], request.user)
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self.get_absolute_url()))

class Transaction(Object):
    time = django.db.models.DateField(auto_now_add=True)
    amount = django.db.models.FloatField(default=0.0)
    pending = django.db.models.BooleanField(default=False)
    tentative = django.db.models.BooleanField(default=True)
    src = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="debit", null=True, blank=True)
    dst = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="credit", null=True, blank=True)
    external_type = django.db.models.CharField(max_length=128, db_index=True, null=True, blank=True)
    external_data = django.db.models.TextField(null=True, blank=True)
    log = django.db.models.TextField(null=True, blank=True)

    class Meta:
        ordering = ('time', )

    @property
    def source(self):
       if self.src:
           return self.src.email
       res = self.external_type
       if self.external_data: res += ": " + self.external_data
       return res

    @property
    def destination(self):
       if self.dst:
           return self.dst.email
       res = self.external_type
       if self.external_data: res += ": " + self.external_data
       return res

    def __unicode__(self):
        data = {
            "time": self.time,
            "src": self.source,
            "dst": self.destination,
            "amount": self.amount
            }
        return "%(time)s: %(src)s -> %(dst)s: %(amount)s" % data

class ThingType(Object):
    barcode_type = django.db.models.CharField(max_length=128, db_index=True)
    barcode_data = django.db.models.CharField(max_length=512, db_index=True)
    name = django.db.models.CharField(default='', blank=True, max_length=256, db_index=True)
    producer = django.db.models.CharField(default='', blank=True, max_length=256, db_index=True)
    designer = django.db.models.CharField(default='', blank=True, max_length=256, db_index=True)
    description = django.db.models.TextField(default='', blank=True)
    log = fcdjangoutils.fields.JsonField(default=[], null=True, blank=True)

    tags = django.db.models.ManyToManyField(appomatic_renderable.models.Tag, null=True, blank=True, related_name='things')

    class Meta:
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
        Object.save(self, *arg, **kw)

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

    def handle__edit(self, request, style):
        form = ThingTypeForm(instance=self)
        return {"form": form}

class ThingTypeForm(django.forms.ModelForm):
    class Meta:
        model = ThingType
        fields = ['name', 'producer', 'designer', 'description']
    tags = django.forms.CharField(widget=django.forms.Textarea(attrs={'rows': 4}), label="Tags")

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

class Thing(Object):
    geoobjects = django.contrib.gis.db.models.GeoManager()

    type = django.db.models.ForeignKey(ThingType, related_name='of_this_type')

    owner = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="owns")
    holder = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="has")

    label_printed = django.db.models.BooleanField(default=False)

    lent_until = django.db.models.DateField(null=True, blank=True)
    deposit_payed =  django.db.models.ForeignKey(Transaction, null=True, blank=True)
    price = django.db.models.FloatField(default=100.0)

    available = django.db.models.BooleanField(default=True)

    location = django.db.models.ForeignKey("Location", related_name="held_here", null=True, blank=True)

    class Meta:
        ordering = ('type__name', )

    def distance(self):
        request = fcdjangoutils.middleware.get_request()
        user = request.user.profile.location
        if not user or not user.position:
            return '-'
        return Thing.geoobjects.filter(id=self.id).distance(user.position, field_name='location__position')[0].distance

    @property
    def request(self):
        if not self.requests.count():
            return None
        return self.requests.order_by('time')[0]

    def lose(self):
        Message.post(
            about = self,
            content = '%(holder)s has lost the thing %(thing)s' % {"holder": self.holder.username, "thing": self.type.name},
            author = self.holder,
            recipients = [self.owner])
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
        if self.holder is None:
            self.holder = self.owner
        if self.holder is not None:
            self.location = self.holder.profile.location
        Object.save(self, *arg, **kw)

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

    def handle__set_price(self, request, style):
        assert request.user.id == self.owner.id
        self.set_price(request.POST['amount'])
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self))

class LendingRequest(Object):
    thing = django.db.models.ForeignKey(Thing, related_name="requests")
    requestor = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="requesting")
    time = django.db.models.DateTimeField(auto_now_add=True)
    time.editable = True

    deposit_payed = django.db.models.ForeignKey(Transaction, null=True, blank=True, related_name="deposit_payed")
    sent = django.db.models.DateTimeField(null=True, blank=True)
    disputed = django.db.models.BooleanField(default=False)
    tracking_barcode_type = django.db.models.CharField(max_length=128, blank=True, db_index=True)
    tracking_barcode_data = django.db.models.CharField(max_length=512, blank=True, db_index=True)

    transport_payed = django.db.models.ForeignKey(Transaction, null=True, blank=True, related_name="transport_payed")
    transport_accepted = django.db.models.FloatField(blank=True)

    @property
    def show_well(self):
        # Used in template... kind of ugly to have here... But too complex logic for the django templating language
        request = fcdjangoutils.middleware.get_request()
        return request.user.id == self.requestor.id or ( request.user.id == self.thing.holder.id and self.sent is None)

    @property
    def overdue(self):
        begining = self.time
        if (self.thing.lent_until is not None and self.thing.lent_until > begining):
            begining = self.thing.lent_until
        return (    self.id == self.thing.request.id
                and self.sent is None
                and datetime.datetime.now() > begining + datetime.timedelta(settings.SENDING_TIME)) 

    def save(self, *arg, **kw):
        if not self.id:
            assert self.requestor.profile.available_balance >= self.thing.type.price

            if self.transport_accepted is None:
                self.transport_accepted = self.requestor.profile.transport_accepted

            self.transport_accepted = min(self.transport_accepted, self.requestor.profile.available_balance - self.thing.type.price)

            deposit_payed = Transaction(
                    amount = self.thing.type.price,
                    src = self.requestor,
                    dst = self.thing.owner,
                    log = unicode(self) + "\n")
            deposit_payed.save()
            self.deposit_payed = deposit_payed

            transport_payed = Transaction(
                    amount = 0.0,
                    src = self.requestor,
                    dst = self.thing.owner,
                    log = unicode(self) + "\n")
            transport_payed.save()
            self.transport_payed = transport_payed
        Object.save(self, *arg, **kw)

    def set_transport_accepted(self, amount):
        available = self.transport_payed.amount + self.requestor.profile.available_balance
        assert amount <= available
        self.transport_accepted = amount
        self.save()

    def set_transport_requested(self, amount):
        assert amount <= self.transport_accepted
        transport_payed = self.transport_payed
        transport_payed.tentative = False
        transport_payed.pending = True
        transport_payed.amount = amount
        transport_payed.save()

    def send(self):
        assert self.sent is None
        self.sent = datetime.datetime.now()
        self.save()

    def dispute(self):
        assert self.sent is not None
        self.disputed = True
        self.save()

    def returned_to_sender(self):
        assert self.disputed
        self.disputed = False
        self.sent = None
        self.save()

    def receive(self):
        thing = self.thing
        thing.holder = self.requestor
        if thing.deposit_payed:
            thing.deposit_payed.delete()
        deposit_payed = self.deposit_payed
        deposit_payed.tentative = False
        deposit_payed.pending = True
        deposit_payed.log += unicode(self.thing) + "\n"
        deposit_payed.save()
        thing.deposit_payed = deposit_payed
        thing.lent_until = datetime.datetime.now() + datetime.timedelta(settings.LENDING_TIME)
        thing.save()
        transport_payed = self.transport_payed
        transport_payed.pending = False
        transport_payed.tentative = False
        transport_payed.save()
        self.delete()

    def simple_cancel(self):
        assert self.sent is None
        self.deposit_payed.delete()
        self.transport_payed.delete()
        self.delete()

    def cancel(self):
        overdue = self.overdue
        thing = self.thing
        self.simple_cancel()
        if overdue:
            thing.lose()

    def comment(self, content, author, recipients=[]):
        extra = [u for u in [self.requestor, self.thing.holder]
                 if u.id != author.id]
        Object.comment(self, content, author, recipients + extra)

    def __unicode__(self):
        return u"%(requestor)s requesting %(thing)s at %(time)s" % {"thing": self.thing, "requestor": self.requestor, "time": self.time}

    def handle__send(self, request, style):
        assert self.thing.holder.id == request.user.id
        self.send()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self.get_absolute_url()))

    def handle__receive(self, request, style):
        assert self.requestor.id == request.user.id
        thing = self.thing
        self.receive()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(thing.get_absolute_url()))

    def handle__cancel(self, request, style):
        assert self.requestor.id == request.user.id
        thing = self.thing
        self.cancel()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(thing.get_absolute_url()))

    def handle__dispute(self, request, style):
        assert self.requestor.id == request.user.id
        self.dispute()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self.get_absolute_url()))

    def handle__returned_to_sender(self, request, style):
        assert self.thing.holder.id == request.user.id
        self.returned_to_sender()
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self.get_absolute_url()))

    def handle__set_transport_accepted(self, request, style):
        self.set_transport_accepted(float(request.POST['amount']))
        if 'set_default' in request.POST:
            request.user.profile.set_transport_accepted(float(request.POST['amount']))
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self.get_absolute_url()))

    def handle__set_transport_requested(self, request, style):
        amount = float(request.POST['amount'])
        if amount <= self.transport_accepted:
            self.set_transport_requested(amount)
        else:
            django.contrib.messages.add_message(request, django.contrib.messages.ERROR, 'Requested amount exceeds maximum cost accepted by the other user.')
        raise fcdjangoutils.responseutils.EarlyResponseException(
            django.shortcuts.redirect(self.get_absolute_url()))


class Message(Object):
    about = django.db.models.ForeignKey(Object, related_name='conversation')
    time = django.db.models.DateTimeField(auto_now_add=True)
    content = django.db.models.TextField(blank=True)

    class Meta:
        ordering = ('time', )

    @property
    def author(self):
        authors = self.users.filter(author=True)
        if authors: return authors[0].user

    @classmethod
    def post(cls, about, content, author, recipients):
        msg = Message(
            about=about,
            content=content,
            )
        msg.save()
        MessageUser(
            user = author,
            message = msg,
            author = True).save()
        for recipient in recipients:
            MessageUser(
                user = recipient,
                message = msg).save()
        return msg

class MessageUser(django.db.models.Model): 
    user = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name='messages')
    message = django.db.models.ForeignKey(Message, related_name='users')
    author = django.db.models.BooleanField(default=False)
    seen = django.db.models.BooleanField(default=False)

    def see(self):
        if not self.seen:
            self.seen = True
            self.save()
        return ""

class Area(django.contrib.gis.db.models.Model):
    objects = django.contrib.gis.db.models.GeoManager()

    name = django.db.models.CharField(default='', max_length=256, db_index=True)
    shape = django.contrib.gis.db.models.PolygonField(geography=True)
    parent = django.db.models.ForeignKey("Area", related_name="children", null=True, blank=True)

class Location(django.contrib.gis.db.models.Model):
    objects = django.contrib.gis.db.models.GeoManager()

    position = django.contrib.gis.db.models.PointField(geography=True, null=True, blank=True)
    area = django.db.models.ForeignKey(Area, related_name="locations", null=True, blank=True)
    address = django.db.models.TextField(default='', blank=True)

class Profile(userena.models.UserenaBaseProfile):
    user = django.db.models.OneToOneField(
        django.contrib.auth.models.User,
        unique=True,
        verbose_name=_('user'),
        related_name='profile')

    location = django.db.models.ForeignKey(Location, related_name="lives_here", null=True, blank=True)
    transport_accepted = django.db.models.FloatField(default=0.0, verbose_name=_('Maximum transport cost accepted'))

    def set_transport_accepted(self, amount):
        self.transport_accepted = amount
        self.save()

    @property
    def tentative_credit(self):
        return self.user.credit.filter(tentative=True).aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0.0

    @property
    def pending_credit(self):
        return self.user.credit.filter(pending=True).aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0.0

    @property
    def credit(self):
        return self.user.credit.filter(tentative=False, pending=False).aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0.0

    @property
    def tentative_debit(self):
        return self.user.debit.filter(tentative=True).aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0.0

    @property
    def pending_debit(self):
        return self.user.debit.filter(pending=True).aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0.0

    @property
    def debit(self):
        return self.user.debit.filter(tentative=False, pending=False).aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0.0

    @property
    def available_balance(self):
        credit = self.user.credit.filter(tentative=False).aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0.0
        debit = self.user.debit.aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0.0
        return credit - debit

    def get_absolute_url(self):
        return 'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse("userena_profile_detail", kwargs={'username': self.user.username})

    @property
    def transaction_history(self):
        return Transaction.objects.filter(django.db.models.Q(src=self.user)|django.db.models.Q(dst=self.user)).order_by('-time')

    @property
    def messages(self):
        return self.user.messages.order_by('message__time')

    @property
    def new_messages(self):
        return self.user.messages.filter(seen=False).order_by('message__time')

    @property
    def has_borrowed(self):
        return self.user.has.filter(~django.db.models.Q(owner=self.user))

    @property
    def has_own(self):
        return self.user.has.filter(owner=self.user, available=True)

    @property
    def lent_own(self):
        return self.user.owns.filter(~django.db.models.Q(holder=self.user))

    @property
    def unavailable_own(self):
        return self.user.has.filter(owner=self.user, available=False)

    @property
    def disputes(self):
        return self.user.has.filter(requests__disputed=True)

    @property
    def needs_labels(self):
        return self.user.owns.filter(label_printed = False)

    @property
    def requests(self):
        return self.user.has.annotate(request_count=django.db.models.Count('requests__id')).filter(request_count__gt = 0, requests__sent = None)


@property
def path(self):
    return "/".join(
        item.name
        for item in self.get_ancestors(include_self=True))
appomatic_renderable.models.Tag.path = path

