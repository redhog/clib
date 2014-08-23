import appomatic_clib.models
import django.forms
import django.shortcuts
from django.utils.translation import ugettext_lazy as _
import django.contrib.messages
import django.contrib.auth.decorators

class FundsForm(django.forms.Form):
    withdraw = django.forms.FloatField(label="Withdraw", required=False)
    add = django.forms.FloatField(label="Deposit", required=False)

@django.contrib.auth.decorators.login_required
def funds(request):
    if request.method == 'GET':
        form = FundsForm()
    else:
        form = FundsForm(request.POST)

        if form.is_valid():
            if 'do_withdraw' in request.POST:
                django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Funds withdrawn.')
            elif 'do_add' in request.POST:
                django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Funds added.')

    return django.shortcuts.render(request, 'appomatic_clib/funds.html', {
        'form': form,
    })
