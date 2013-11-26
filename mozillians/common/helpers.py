from hashlib import md5

from django.conf import settings
from django.http import HttpResponseRedirect
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe

import bleach
import markdown as markdown_module
from funfactory.helpers import urlparams
from funfactory.urlresolvers import reverse
from funfactory import utils
from jingo import register
from jinja2 import Markup, contextfunction
from sorl.thumbnail import get_thumbnail


GRAVATAR_URL = 'https://secure.gravatar.com/avatar/{emaildigest}'


@register.function
def absolutify(url):
    return utils.absolutify(url)


def gravatar(email, default_avatar_url=settings.DEFAULT_AVATAR_URL,
             size=175, rating='pg'):
    """Return the Gravatar URL for an email address."""
    url = GRAVATAR_URL.format(emaildigest=md5(email).hexdigest())
    url = urlparams(url, d=utils.absolutify(default_avatar_url),
                    s=size, r=rating)
    return url


@register.function
def field_with_attrs(bfield, **kwargs):
    """Allows templates to dynamically add html attributes to bound
    fields from django forms.

    Copied from bedrock.
    """
    if kwargs.get('label', None):
        bfield.label = kwargs['label']
    bfield.field.widget.attrs.update(kwargs)
    return bfield


@register.function
def bootstrap(element):
    """Renders bootstrap forms in jinja2.

    Takes an element that is either a field or an entire form and
    renders the appropriate bootstrap elements.
    """
    element_type = element.__class__.__name__.lower()
    if element_type == 'boundfield':
        template = get_template("bootstrapform/field.html")
        context = Context({'field': element})
    else:
        template = get_template("bootstrapform/form.html")
        context = Context({'form': element})

    return mark_safe(template.render(context))


@register.function
def thumbnail(img, geometry, **kwargs):
    """Proxy to solr's get_thumbnail."""
    return get_thumbnail(img, geometry, **kwargs)


def redirect(to, *args, **kwargs):
    """Redirect with locale support."""
    url = reverse(to, args=args, kwargs=kwargs)
    return HttpResponseRedirect(url)


@register.filter
def markdown(text, allowed_tags=None, allowed_attributes=None, allowed_styles=None):
    if not allowed_tags:
        allowed_tags = ['p', 'em', 'li', 'ul', 'a', 'strong']
    if not allowed_attributes:
        allowed_attributes = ['href']
    if not allowed_styles:
        allowed_styles = []
    text = markdown_module.markdown(text, safe_mode='remove')
    clean_text = bleach.clean(text, allowed_tags, allowed_attributes, allowed_styles, strip=True)
    return Markup(clean_text)


@register.function
@contextfunction
def display_context(context, include_callables=False):
    """
    Return a marked-up chunk of content containing the items
    in the template context, if ``settings.DEBUG`` is True.
    Otherwise returns an empty string.

    By default, callables are omitted. Pass include_callables=True
    to include them.

    The format of the result is::

        <dl class="jinja-context">
          <dt>key</dt><dd>value</dd>
          <dt>key</dt><dd>value</dd>
          ...
        </dl>

    ``repr`` is applied to the values to format them.

    Example usage::

        {{ display_context() }}

        {{ display_context(include_callables=True) }}

    """
    if not settings.DEBUG:
        return ""
    keys = sorted(context.keys())
    parts = [
        '<dt>{key}</dt><dd>{value}</dd>'.format(key=key, value=repr(context[key]))
        for key in keys
        if include_callables or not callable(context[key])
    ]
    html = '<dl class="jinja-context">{parts}</dl>'.format(parts=''.join(parts))
    return Markup(html)


@register.function
@contextfunction
def get_context(context):
    """
    Provide access to the Jinja :class:`Context` object in case
    you want to do more complicated things with it. Typically,
    ``display_context()`` is easier to use.

    If ``settings.DEBUG`` is not True, returns an empty dictionary.

    Example usage::

        {% set context=get_context() %}
        {% for k, v in context|dictsort %}
            {% if not is_callable(v) %}
                {{ k }}: {{ v }}<br/>
            {% endif %}
        {% endfor %}
    """
    if not settings.DEBUG:
        return {}
    return context


@register.function
def is_callable(thing):
    """
    Return True if thing is callable.

    See get_context() for example usage.
    """
    return callable(thing)
