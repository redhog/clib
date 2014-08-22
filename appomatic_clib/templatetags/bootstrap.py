import django.template

register = django.template.Library()

@register.filter(is_safe=True)
def formControl(value, *arg):
    return value.as_widget(attrs={'class': 'form-control'})
