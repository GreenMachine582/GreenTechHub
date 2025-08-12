import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.inclusion_tag("querybuilder/widget.html", takes_context=True)
def render_querybuilder(context, *, config_id, fields, target="#qb-filters", initial=None, compact=False):
    """
    Renders the QueryBuilder UI.

    Args:
        config_id (str): unique id for this config. Used to store fields in window.__QB_CONFIGS__[config_id]
        fields (list[dict]): e.g. [{'name': 'title', 'label': 'Title', 'type': 'string'}, ...]
        target (str): CSS selector for the hidden input to write JSON into (e.g. '#id_filters')
        initial (dict): initial rules tree
        compact (bool): compact mode
    """
    return {
        "config_id": config_id,
        "target": target,
        "compact": compact,
        "fields_json": mark_safe(json.dumps(fields)),
        "initial": json.dumps(initial) if initial else "",
    }
