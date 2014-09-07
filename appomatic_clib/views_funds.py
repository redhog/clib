import appomatic_clib.models
import django.forms
import django.shortcuts
from django.utils.translation import ugettext_lazy as _
import django.contrib.messages
import django.contrib.auth.decorators
import django.contrib.auth.models
import django.contrib.sites.models
from django.conf import settings
import urllib2
import urllib
import json

def paypal_withdraw(request, user, amount):
    if amount > user.profile.available_balance:
        raise Exception("Too little funds available")

    req = {
        "actionType": "PAY",
        "feesPayer": "EACHRECEIVER",
        "currencyCode": "EUR",
        "receiverList": [{
                "receiver": {
                    "amount": amount,
                    "email": user.email
                    },
                }],
        "sender": {
            "useCredentials": True
            },
        "requestEnvelope": {},
        "cancelUrl": "http://example.com/cancel",
        "returnUrl": "http://example.com/return"
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
        raise Exception(res["error"][0]["message"])
        
    transaction.amount = res["paymentInfoList"]["paymentInfo"][0]["receiver"]["amount"]

    transaction.tentative = False
    transaction.log += json.dumps(res) + "\n"

    if res["paymentExecStatus"] != "COMPLETED":
        transaction.pending = True
        transaction.save()
        raise Exception(res["error"]["message"])

    transaction.save()

    django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Funds withdrawn.')

def paypal_add(request, user, amount):
    req = {
        "actionType": "PAY",
        "feesPayer": "SENDER",
        "currencyCode": "EUR",
        "receiverList": [{
                "receiver": {
                    "amount": amount,
                    "email": settings.PAYPAL_EMAIL
                    },
                }],
        "senderEmail": user.email,
        "requestEnvelope": {},
        "cancelUrl": 'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse('appomatic_clib.views_funds.funds'),
        "returnUrl": 'http://' + django.contrib.sites.models.Site.objects.get_current().domain + django.core.urlresolvers.reverse('appomatic_clib.views_funds.paypal_add_return') + "?payKey=${payKey}",
        }
    req = json.dumps(req)

    httpReq = urllib2.Request(url=settings.PAYPAL_ENDPOINTS['PAY'],
                              data=req,
                              headers=settings.PAYPAL_HEADERS)
    res = json.load(urllib2.urlopen(httpReq))

    return django.shortcuts.redirect(settings.PAYPAL_REDIRECT % res)


def paypal_add_return(request):
    req = {
        "payKey": request.GET['payKey'],
        "requestEnvelope": {},
        }
    req = json.dumps(req)

    httpReq = urllib2.Request(url=settings.PAYPAL_ENDPOINTS['PAYMENT_DETAILS'],
                              data=req,
                              headers=settings.PAYPAL_HEADERS)
    res = json.load(urllib2.urlopen(httpReq))

    assert res['status'] == 'COMPLETED'
    assert res['actionType'] == 'PAY'
    assert res['currencyCode'] == 'EUR'
    assert res['feesPayer'] == 'SENDER'
    assert res['paymentInfoList']['paymentInfo'][0]['receiver']['email'] == settings.PAYPAL_EMAIL

    user = django.contrib.auth.models.User.objects.get(email = res['senderEmail'])
    amount = res['paymentInfoList']['paymentInfo'][0]['receiver']['amount']

    transaction = appomatic_clib.models.Transaction(
        pending = False,
        tentative = False,
        amount = amount,
        src = None,
        dst = user,
        external_type = "paypal",
        external_data = user.email,
        log = json.dumps(res) + "\n")
    transaction.save()

    django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Funds added.')
                
    return django.shortcuts.redirect('appomatic_clib.views_funds.funds')

def fake_withdraw(request, user, amount):
    transaction = appomatic_clib.models.Transaction(
        amount = amount,
        src = user,
        dst = None,
        external_type = "fake",
        external_data = user.email,
        tentative = False,
        pending = False)
    transaction.save()
    django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Funds withdrawn.')


def fake_add(request, user, amount):
    transaction = appomatic_clib.models.Transaction(
        pending = False,
        tentative = False,
        amount = amount,
        src = None,
        dst = user,
        external_type = "fake",
        external_data = user.email)
    transaction.save()

    django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Funds added.')
                
    return django.shortcuts.redirect('appomatic_clib.views_funds.funds')

services = {
    'paypal': {
        'name': 'PayPal',
        'withdraw': paypal_withdraw,
        'add': paypal_add
        }
    }

if getattr(settings, 'CLIB_FAKE_MONEY', False):
    services = {
        'fake': {
            'name': 'Fake',
            'withdraw': fake_withdraw,
            'add': fake_add
            }
        }


class FundsForm(django.forms.Form):
    amount = django.forms.FloatField(label="Amount", required=False)
    service = django.forms.ChoiceField(label="Service", choices=[(key, service['name']) for (key, service) in services.iteritems()])

@django.contrib.auth.decorators.login_required
def funds(request):
    if request.method == 'GET':
        form = FundsForm()
    else:
        form = FundsForm(request.POST)

        if form.is_valid():
            service = services[form.cleaned_data['service']]
            if 'do_withdraw' in request.POST:
                try:
                    service['withdraw'](request, request.user, form.cleaned_data['amount'])
                except Exception, e:
                    django.contrib.messages.add_message(request, django.contrib.messages.ERROR, unicode(e))
                else:
                    django.contrib.messages.add_message(request, django.contrib.messages.INFO, 'Funds withdrawn.')
            elif 'do_add' in request.POST:
                return service['add'](request, request.user, form.cleaned_data['amount'])

    return django.shortcuts.render(request, 'appomatic_clib/funds.html', {
        'form': form,
    })
