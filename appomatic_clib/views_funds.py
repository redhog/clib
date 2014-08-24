import appomatic_clib.models
import django.forms
import django.shortcuts
from django.utils.translation import ugettext_lazy as _
import django.contrib.messages
import django.contrib.auth.decorators
from django.conf import settings
import urllib2
import urllib
import json

def paypal_withdraw(user, amount):
    if amount > user.profile.available_balance:
        raise Exception("Too little funds available")

    req = {
        "actionType": "PAY",
        "cancelUrl": "http://example.com/cancel",
        "currencyCode": "EUR",
        "receiverList": [{
                "receiver": {
                    "amount": amount,
                    "email": user.email
                    },
                }],
        "returnUrl": "http://example.com/return",
        "sender": {
            "useCredentials": True
            },
        "requestEnvelope": {
            }
        }
    req = json.dumps(req)

    transaction = appomatic_clib.models.Transaction(
        amount = amount,
        src = user,
        dst = None,
        external_type = "paypal",
        external_data = user.email,
        log = req + "\n")
    transaction.save()


    httpReq = urllib2.Request(url=settings.PAYPAL_ENDPOINTS['PAY'],
                              data=req,
                              headers=settings.PAYPAL_HEADERS)
    res = json.load(urllib2.urlopen(httpReq))

    if res["responseEnvelope"]["ack"] != "Success":
        transaction.delete()
        raise Exception(res["error"]["message"])
        
    transaction.amount = res["paymentInfoList"]["paymentInfo"][0]["receiver"]["amount"]

    transaction.tentative = False
    transaction.log += json.dumps(res) + "\n"

    if res["paymentExecStatus"] != "COMPLETED":
        transaction.pending = True
        transaction.save()
        raise Exception(res["error"]["message"])

    transaction.save()
    

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
                try:
                    paypal_withdraw(request.user, form.cleaned_data['withdraw'])
                except Exception, e:
                    django.contrib.messages.add_message(request, django.contrib.messages.ERROR, unicode(e))
                else:
                    django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Funds withdrawn.')
            elif 'do_add' in request.POST:
                
                django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Funds added.')

    return django.shortcuts.render(request, 'appomatic_clib/funds.html', {
        'form': form,
    })
