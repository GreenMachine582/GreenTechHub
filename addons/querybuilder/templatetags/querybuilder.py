import json
from django import template
from django.utils.safestring import mark_safe
from django.utils.text import slugify

register = template.Library()

@register.inclusion_tag("querybuilder/widget.html", takes_context=True)
def render_querybuilder(context, *, config_id, fields=None, name: str = "filters", target=None, input_id=None, initial=None, compact=False, collapsed=False):
    """
    Renders the QueryBuilder UI.

    Args:
        config_id (str): unique id for config, used as key in window.__QB_CONFIGS__[config_id]
        fields (list[dict]): [{'name': 'title', 'label': 'Title', 'type': 'string'}, ...]
        name (str): name attribute for the hidden input (default: "filters")
        target (str|None): CSS selector for an existing hidden input. If None, we render one.
        input_id (str|None): id attribute for the auto-rendered hidden input
        initial (dict): initial rules tree
        compact (bool): compact mode
        collapsed (bool): start collapsed (if your JS supports it)
    """
    fields = fields or context.get(f"{config_id}_fields", context.get("qb-fields", []))
    input_id = input_id or f"qb-{slugify(config_id)}-{slugify(name)}"
    auto_input = not bool(target)
    target_selector = target or f"#{input_id}"

    return {
        "config_id": config_id,
        "fields_json": mark_safe(json.dumps(fields)),
        "initial": json.dumps(initial) if initial else "",
        "compact": compact,
        "collapsed": collapsed,
        "auto_input": auto_input,
        "input_id": input_id,
        "name": name,
        "target": target_selector,
    }
