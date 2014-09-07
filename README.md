# Installation

    virtualenv myserver
    cd myserver
    source bin/activate
    
    mkdir apps
    cd apps
    git clone
    git@github.com:redhog/clib.git
    
    mkdir appomatic_config
    touch appomatic_config/__init__.py
    touch appomatic_config/__app__.py
    echo > appomatic_config/__settings__.py <<EOF
    
    import os.path
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'HOST': 'localhost',
            'NAME': 'clib',
            'USER': 'clib',
            'PASSWORD': 'XXXXXXXXXXX',
        }
    }
    PAYPAL_EMAIL="test@example.com"
    PAYPAL_ENDPOINTS = {
       "PAY": "https://svcs.sandbox.paypal.com/AdaptivePayments/Pay",
       "PAYMENT_DETAILS": "https://svcs.sandbox.paypal.com/AdaptivePayments/PaymentDetails"
    }
    PAYPAL_HEADERS = {
        "X-PAYPAL-SECURITY-USERID": "test_api1.example.com",
        "X-PAYPAL-SECURITY-PASSWORD": "XXXXXXXXXXXXXXXX",
        "X-PAYPAL-SECURITY-SIGNATURE": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "X-PAYPAL-APPLICATION-ID": "APP-80W284485P519543T",
        "X-PAYPAL-REQUEST-DATA-FORMAT": "JSON"
    }
    PAYPAL_REDIRECT="https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_ap-payment&paykey=%(payKey)s"
    
    EOF

    appomatic syncdb
    
# Running

    cd myserver
    source bin/activate
    appomatic runserver


