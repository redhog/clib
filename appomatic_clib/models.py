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

class Transaction(django.db.models.Model):
    time = django.db.models.DateField(auto_now_add=True)
    amount = django.db.models.FloatField(default=0.0)
    pending = django.db.models.BooleanField(default=False)
    tentative = django.db.models.BooleanField(default=True)
    src = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="debit", null=True, blank=True)
    dst = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="credit", null=True, blank=True)
    external_type = django.db.models.CharField(max_length=128, db_index=True, null=True, blank=True)
    external_data = django.db.models.TextField(null=True, blank=True)
    log = django.db.models.TextField(null=True, blank=True)

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

class ThingType(django.db.models.Model):
    barcode_type = django.db.models.CharField(max_length=128, db_index=True)
    barcode_data = django.db.models.CharField(max_length=512, db_index=True)
    name = django.db.models.CharField(default='', max_length=256, db_index=True)
    producer = django.db.models.CharField(default='', max_length=256, db_index=True)
    designer = django.db.models.CharField(default='', max_length=256, db_index=True)
    description = django.db.models.TextField(default='')

    def save(self, *arg, **kw):
        if self.barcode_type == 'EAN_13' and self.name == '' and self.designer == '':
            self.designer, self.name = appomatic_clib.isbnlookup.ISBNLookup.lookup(self.barcode_data)
        django.db.models.Model.save(self, *arg, **kw)

    @classmethod
    def get(cls, barcode_type, barcode_data, **kw):
        existing = cls.objects.filter(barcode_type=barcode_type, barcode_data=barcode_data)
        if existing:
            return existing[0]
        tt = cls(barcode_type=barcode_type, barcode_data=barcode_data, **kw)
        tt.save()
        return tt

    @property
    def price(self):
        return self.of_this_type.aggregate(django.db.models.Avg('price'))['price__avg']

    def __unicode__(self):
        return u"%(name)s: %(barcode_type)s/%(barcode_data)s" % {"name": self.name, "barcode_type": self.barcode_type, "barcode_data": self.barcode_data}

    def get_absolute_url(self):
        return 'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse("appomatic_clib.views.thing_type", kwargs={'id': self.id})


class Thing(django.db.models.Model):
    id = django.db.models.CharField(max_length=128, primary_key=True)

    type = django.db.models.ForeignKey(ThingType, related_name='of_this_type')

    owner = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="owns")
    holder = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="has")

    label_printed = django.db.models.BooleanField(default=False)

    lent_until = django.db.models.DateField(null=True, blank=True)
    deposit_payed =  django.db.models.ForeignKey(Transaction, null=True, blank=True)
    price = django.db.models.FloatField(default=100.0)

    def distance(self):
        request = fcdjangoutils.middleware.get_request()
        if not request.user.is_authenticated() or not request.user.profile or not self.holder or not self.holder.profile:
            return ''
        user = request.user.profile.location
        holder = self.holder.profile.location
        if not user or not holder or not user.position:
            return ''
        return user.position.distance(
            holder.position)

    @property
    def request(self):
        if not self.requests.count():
            return None
        return self.requests.order_by('time')[0]

    def save(self, *arg, **kw):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.holder is None:
            self.holder = self.owner
        django.db.models.Model.save(self, *arg, **kw)

    def __unicode__(self):
        return u"%(type)s: %(id)s owned by %(owner)s" % {"type": self.type, "id": self.id, "owner": self.owner}

    def get_absolute_url(self):
        return 'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse("appomatic_clib.views.thing", kwargs={'id': self.id})

class LendingRequest(django.db.models.Model):
    thing = django.db.models.ForeignKey(Thing, related_name="requests")
    requestor = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="requesting")
    time = django.db.models.DateTimeField(auto_now_add=True)

    deposit_payed = django.db.models.ForeignKey(Transaction, null=True, blank=True)
    sent = django.db.models.BooleanField(default=False)
    tracking_barcode_type = django.db.models.CharField(max_length=128, db_index=True)
    tracking_barcode_data = django.db.models.CharField(max_length=512, db_index=True)

    def save(self, *arg, **kw):
        if self.id is None:
            assert self.requestor.profile.available_balance > self.thing.type.price            
            self.deposit_payed = Transaction(
                    amount = self.thing.type.price,
                    src = self.requestor,
                    dst = self.thing.owner,
                    log = unicode(self) + "\n")
            self.deposit_payed.save()
        django.db.models.Model.save(self, *arg, **kw)

    def send(self):
        self.sent = True
        self.save()

    def receive(self):
        self.thing.holder = self.requestor
        if self.thing.deposit_payed:
            self.thing.deposit_payed.delete()
        self.thing.deposit_payed = self.deposit_payed
        self.thing.deposit_payed.tentative = False
        self.thing.deposit_payed.pending = True
        self.thing.deposit_payed.log += unicode(self.thing) + "\n"
        self.thing.save()
        self.delete()

    def __unicode__(self):
        return u"%(requestor)s requesting %(thing)s at %(time)s" % {"thing": self.thing, "requestor": self.requestor, "time": self.time}

    def get_absolute_url(self):
        return 'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse("appomatic_clib.views.lending_request", kwargs={'id': self.id})

def needs_labels(self):
    return self.owns.filter(label_printed = False)
django.contrib.auth.models.User.needs_labels = needs_labels

def requests(self):
    return self.has.filter(requests__sent = False)
django.contrib.auth.models.User.requests = requests

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
    objects = django.contrib.gis.db.models.GeoManager()

    user = django.db.models.OneToOneField(
        django.contrib.auth.models.User,
        unique=True,
        verbose_name=_('user'),
        related_name='profile')

    location = django.db.models.ForeignKey(Location, related_name="lives_here", null=True, blank=True)

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
