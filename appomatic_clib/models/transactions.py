import django.db.models
import django.contrib.auth
from . import base

class Transaction(base.Object):
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
        app_label = 'appomatic_clib'
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
