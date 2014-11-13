import datetime
import django.shortcuts
import django.db.models
import django.contrib.auth.models
from django.conf import settings
import fcdjangoutils.responseutils
import fcdjangoutils.middleware
import appomatic_djangoobjfeed.models
from . import base
from . import transactions


class OwnershipTransfer(base.Object):
    class Meta:
        app_label = 'appomatic_clib'
    time = django.db.models.DateTimeField(auto_now_add=True)
    time.editable = True
    thing = django.db.models.ForeignKey("Thing", related_name='ownership_transfers')
    old_owner = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="old_ownerships")
    new_owner = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="new_ownerships")

    def get_absolute_url(self):
        raise NotImplementedError

class Lost(OwnershipTransfer):
    affected = django.db.models.ForeignKey(django.contrib.auth.models.User, null=True, related_name="affected")

    class Meta:
        app_label = 'appomatic_clib'

class LostFeedEntry(appomatic_djangoobjfeed.models.ObjFeedEntry):
    class Meta:
        app_label = 'appomatic_clib'

    obj = django.db.models.ForeignKey(Lost, related_name='feed_entry')

    @classmethod
    def get_author_from_obj(cls, obj):
        return obj.new_owner

    @classmethod
    def holder_feeds_for_obj(cls, instance, author):
        yield lambda feed_entry: True, instance.old_owner.feed
        if instance.affected: yield lambda feed_entry: True, instance.affected.feed

    def render__title(self, request, context):
        return 'Thing got lost'

class LendingRequest(base.Object):
    class Meta:
        app_label = 'appomatic_clib'
    thing = django.db.models.ForeignKey("Thing", related_name="requests")
    requestor = django.db.models.ForeignKey(django.contrib.auth.models.User, related_name="requesting")
    time = django.db.models.DateTimeField(auto_now_add=True)
    time.editable = True

    deposit_payed = django.db.models.ForeignKey(transactions.Transaction, null=True, blank=True, related_name="deposit_payed")
    sent = django.db.models.DateTimeField(null=True, blank=True)
    disputed = django.db.models.BooleanField(default=False)
    tracking_barcode_type = django.db.models.CharField(max_length=128, blank=True, db_index=True)
    tracking_barcode_data = django.db.models.CharField(max_length=512, blank=True, db_index=True)

    transport_payed = django.db.models.ForeignKey(transactions.Transaction, null=True, blank=True, related_name="transport_payed")
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

            deposit_payed = transactions.Transaction(
                    amount = self.thing.type.price,
                    src = self.requestor,
                    dst = self.thing.owner,
                    log = unicode(self) + "\n")
            deposit_payed.save()
            self.deposit_payed = deposit_payed

            transport_payed = transactions.Transaction(
                    amount = 0.0,
                    src = self.requestor,
                    dst = self.thing.owner,
                    log = unicode(self) + "\n")
            transport_payed.save()
            self.transport_payed = transport_payed
        base.Object.save(self, *arg, **kw)

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
        deposit_payed = self.deposit_payed
        transport_payed = self.transport_payed
        self.delete()
        deposit_payed.delete()
        transport_payed.delete()

    def cancel(self):
        overdue = self.overdue
        thing = self.thing
        self.simple_cancel()
        if overdue:
            thing.lose()

    def comment(self, content, author, recipients=[]):
        extra = [u for u in [self.requestor, self.thing.holder]
                 if u.id != author.id]
        base.Object.comment(self, content, author, recipients + extra)

    def __unicode__(self):
        return u"%(requestor)s requesting %(thing)s at %(time)s" % {"thing": self.thing.type, "requestor": self.requestor, "time": self.time}

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

class LendingRequestFeed(appomatic_djangoobjfeed.models.ObjFeed):
    class Meta:
        app_label = 'appomatic_clib'
    owner = django.db.models.OneToOneField(LendingRequest, primary_key=True, related_name="feed")

    def allowed_to_post(self, user = None):
        if user is None: user = fcdjangoutils.middleware.get_request().user
        return user.id in (self.owner.requestor.id, self.owner.thing.holder.id, self.owner.thing.owner.id)


class LendingRequestEntry(appomatic_djangoobjfeed.models.ObjFeedEntry):
    class Meta:
        app_label = 'appomatic_clib'

    obj = django.db.models.ForeignKey(LendingRequest, related_name='feed_entry')

    @classmethod
    def get_author_from_obj(cls, obj):
        return obj.requestor

    def render__title(self, request, context):
        return 'Lending request'

    @classmethod
    def holder_feeds_for_obj(cls, instance, author):
        yield lambda feed_entry: True, instance.thing.holder.feed

@classmethod
def actor_feeds_for_obj(cls, instance, author):
    if hasattr(instance, "feed"):
        if hasattr(instance.feed.owner, "requestor"):
            yield lambda feed_entry: True, instance.feed.owner.requestor.feed
            if hasattr(instance.feed.owner, "thing") and hasattr(instance.feed.owner.thing, "holder"):
                yield lambda feed_entry: True, instance.feed.owner.thing.holder.feed
appomatic_djangoobjfeed.models.ObjFeedEntry.actor_feeds_for_obj = actor_feeds_for_obj

def allowed_to_post_comment(self, user):
    return False
appomatic_djangoobjfeed.models.ObjFeedEntry.allowed_to_post_comment = allowed_to_post_comment
