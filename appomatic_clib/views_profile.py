import appomatic_clib.models
import django.contrib.auth.models
import django.forms
import django.shortcuts
import django.contrib.gis.forms.fields
from django.utils.translation import ugettext_lazy as _
import django.contrib.messages

class ProfileForm(django.forms.ModelForm):
    password1 = django.forms.CharField(label="Password", widget=django.forms.PasswordInput, required=False)
    password2 = django.forms.CharField(label=_('Re-Enter your password'), widget=django.forms.PasswordInput, required=False)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data['password2']
        if password1 != password2:
            raise forms.ValidationError(_("The passwords you entered did not match!"))
        return password2

    def save(self, commit=True):
        user = super(ProfileForm, self).save(commit=False)
        if (self.cleaned_data["password1"]):
            print "set", self.cleaned_data["password1"]
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

    class Meta:
        model = django.contrib.auth.models.User
        fields = ('first_name','last_name','email')

class LocationForm(django.forms.ModelForm):
    class Meta:
        model = appomatic_clib.models.Location
        fields = ('address','position')

def profile(request):
    if request.method == 'GET':
        form = ProfileForm(instance=request.user)
        form.location = LocationForm(instance=request.user.profile.location)
    else:
        form = ProfileForm(request.POST, instance=request.user)
        form.location = LocationForm(request.POST, instance=request.user.profile.location)

        if form.is_valid():
            user = form.save()
            location = form.location.save()
            profile = user.profile
            profile.location = location
            profile.save()

            django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Changes saved.')

    return django.shortcuts.render(request, 'appomatic_clib/profile.html', {
        'form': form,
    })
