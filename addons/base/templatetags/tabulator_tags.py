
import json

from django import template
from django.utils.html import format_html

register = template.Library()

@register.simple_tag
def render_tabulator(div_id, url_path, columns, page_size=50, template_field=None, template_id=None):
    """
    Renders a <div> for Tabulator _and_ optionally wires up a
    ${…}-templated column formatter.
    - div_id:         the HTML id attribute to use
    - url_path:  e.g. "pyfinbot/stocks/"
    - columns:        a Python list-of-dicts, e.g.
        [
          {"title":"Symbol","field":"symbol","sorter":"string","headerFilter":"input"},
          …
        ]
    - page_size:      remote pagination page size
    - template_field:  name of the column to decorate (e.g. "actions")
    - template_id:     id of a <script type="text/template"> in your page
    """
    return format_html(
        '<div id="{div_id}" '
        'class="tabulator-widget" '
        'data-path="{url_path}" '
        "data-columns='{cols}' "
        'data-page-size="{page_size}" '
        '{tpl_field}{tpl_id} '
        'style="height:60vh;"></div>',
        div_id=div_id,
        url_path=url_path,
        cols=json.dumps(columns),
        page_size=page_size,
        tpl_field=format_html('data-template-field="{}"', template_field) if template_field else "",
        tpl_id=format_html('data-template-id="{}"', template_id) if template_id else ""
    )
