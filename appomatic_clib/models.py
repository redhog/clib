import django.db.models
import django.contrib.auth.models
import django.core.urlresolvers
import django.contrib.sites.models

class ThingType(django.db.models.Model):
    barcode_type = django.db.models.CharField(max_length=128, db_index=True)
    barcode_data = django.db.models.CharField(max_length=512, db_index=True)
    name = django.db.models.CharField(default='', max_length=256, db_index=True)
    description = django.db.models.TextField(default='')

    @classmethod
    def get(cls, barcode_type, barcode_data):
        existing = cls.objects.filter(barcode_type=barcode_type, barcode_data=barcode_data)
        if existing:
            return existing[0]
        tt = cls(barcode_type=barcode_type, barcode_data=barcode_data)
        tt.save()
        return tt

    def __unicode__(self):
        return u"%(name)s: %(barcode_type)s/%(barcode_data)s" % {"name": self.name, "barcode_type": self.barcode_type, "barcode_data": self.barcode_data}

    def get_absolute_url(self):
        return django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse("appomatic_clib.views.thing_type", kwargs={'id': self.id})


class Thing(django.db.models.Model):
    type = django.db.models.ForeignKey(ThingType, related_name='of_this_type')

    owner = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="owns")
    holder = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="has")

    @property
    def request(self):
        if not self.requests.count():
            return None
        return self.requests.order_by('time')[0]

    def save(self, *arg, **kw):
        if self.holder is None:
            self.holder = self.owner
        django.db.models.Model.save(self, *arg, **kw)

    def __unicode__(self):
        return u"%(type)s: %(id)s owned by %(owner)s" % {"type": self.type, "id": self.id, "owner": self.owner}

    def get_absolute_url(self):
        return django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse("appomatic_clib.views.thing", kwargs={'id': self.id})

class LendingRequest(django.db.models.Model):
    thing = django.db.models.ForeignKey(Thing, related_name="requests")
    requestor = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="requesting")
    time = django.db.models.DateTimeField(auto_now_add=True)

    sent = django.db.models.BooleanField(default=False)
    tracking_barcode_type = django.db.models.CharField(max_length=128, db_index=True)
    tracking_barcode_data = django.db.models.CharField(max_length=512, db_index=True)

    def send(self):
        self.sent = True
        self.save()

    def receive(self):
        self.thing.holder = self.requestor
        self.thing.save()
        self.delete()

    def __unicode__(self):
        return u"%(requestor)s requesting %(thing)s at %(time)s" % {"thing": self.thing, "requestor": self.requestor, "time": self.time}
