import appomatic_clib.models
import django.contrib.auth.models
import django.forms
import django.shortcuts
import django.contrib.gis.forms.fields
from django.utils.translation import ugettext_lazy as _
import django.contrib.messages

class UserForm(django.forms.ModelForm):
    # password1 = django.forms.CharField(label="Password", widget=django.forms.PasswordInput, required=False)
    # password2 = django.forms.CharField(label=_('Re-Enter your password'), widget=django.forms.PasswordInput, required=False)

    # def clean_password2(self):
    #     password1 = self.cleaned_data.get("password1", "")
    #     password2 = self.cleaned_data['password2']
    #     if password1 != password2:
    #         raise forms.ValidationError(_("The passwords you entered did not match!"))
    #     return password2

    # def save(self, commit=True):
    #     user = super(UserForm, self).save(commit=False)
    #     if (self.cleaned_data["password1"]):
    #         print "set", self.cleaned_data["password1"]
    #         user.set_password(self.cleaned_data["password1"])
    #     if commit:
    #         user.save()
    #     return user

    class Meta:
        model = django.contrib.auth.models.User
        fields = ('first_name','last_name')

class ProfileForm(django.forms.ModelForm):
    class Meta:
        model = appomatic_clib.models.Profile
        fields = ('mugshot','privacy')

class LocationForm(django.forms.ModelForm):
    class Meta:
        model = appomatic_clib.models.Location
        fields = ('address','position')

def edit(request, username):
    assert username == request.user.username
    if request.method == 'GET':
        form = UserForm(instance=request.user)
        form.profile = ProfileForm(instance=request.user.profile)
        form.location = LocationForm(instance=request.user.profile.location)
    else:
        form = UserForm(request.POST, instance=request.user)
        form.profile = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        form.location = LocationForm(request.POST, instance=request.user.profile.location)

        if form.is_valid():
            user = form.save()
            user.profile = form.profile.save()
            user.profile.location = form.location.save()
            user.profile.save()
            user.save()

            django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Changes saved.')

    return django.shortcuts.render(request, 'appomatic_clib/profile.html', {
        'form': form,
    })
