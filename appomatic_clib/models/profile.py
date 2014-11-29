import django.db.models
import django.contrib.gis.db.models
import userena.models
from django.utils.translation import ugettext as _
from . import transactions

class Area(django.contrib.gis.db.models.Model):
    class Meta:
        app_label = 'appomatic_clib'
    objects = django.contrib.gis.db.models.GeoManager()

    name = django.db.models.CharField(default='', max_length=256, db_index=True)
    shape = django.contrib.gis.db.models.PolygonField(geography=True)
    parent = django.db.models.ForeignKey("Area", related_name="children", null=True, blank=True)

class Location(django.contrib.gis.db.models.Model):
    class Meta:
        app_label = 'appomatic_clib'
    objects = django.contrib.gis.db.models.GeoManager()

    position = django.contrib.gis.db.models.PointField(geography=True, null=True, blank=True)
    area = django.db.models.ForeignKey(Area, related_name="locations", null=True, blank=True)
    address = django.db.models.TextField(default='', blank=True)

class Profile(userena.models.UserenaBaseProfile):
    class Meta:
        app_label = 'appomatic_clib'
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
        return transactions.Transaction.objects.filter(django.db.models.Q(src=self.user)|django.db.models.Q(dst=self.user)).order_by('-time')

    @property
    def messages(self):
        return self.user.feed.entries

    @property
    def new_messages(self):
        return self.user.feed.new_entries

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
    def things_needs_labels(self):
        return self.user.owns.filter(label_printed = False)

    @property
    def shelfs_needs_labels(self):
        return self.user.shelfs.filter(label_printed = False)

    @property
    def requests(self):
        return self.user.has.annotate(request_count=django.db.models.Count('requests__id')).filter(request_count__gt = 0, requests__sent = None)
