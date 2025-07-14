
import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def render_tabulator(div_id, url_path, columns, page_size=50):
    """
    Renders the container for a Tabulator table.
    - div_id:         the HTML id attribute to use
    - url_path:  e.g. "pyfinbot/stocks/"
    - columns:        a Python list-of-dicts, e.g.
        [
          {"title":"Symbol","field":"symbol","sorter":"string","headerFilter":"input"},
          …
        ]
    - page_size:      remote pagination page size
    """
    html = (
      f'<div id="{div_id}" '
      f'class="tabulator-widget" '
      f'data-path="{url_path}" '
      f'data-columns=\'{json.dumps(columns)}\' '
      f'data-page-size="{page_size}" '
      f'style="height:60vh;"></div>'
    )
    return mark_safe(html)
