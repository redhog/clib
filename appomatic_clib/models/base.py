import uuid
import django.db.models
import django.contrib.sites.models
import django.core.urlresolvers
import appomatic_renderable.models
import fcdjangoutils.modelhelpers

class Object(django.db.models.Model, appomatic_renderable.models.Renderable):
    class Meta:
        app_label = 'appomatic_clib'
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
