
import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def render_tabulator(context, path=None, table_id="records-table", columns=None, page_size=0,
                     template_field=None, template_id=None):
    """
    Renders an empty <div> for Tabulator and registers defaults
    pulled from the view or passed args into window.tabulatorDefaults[table_id].
    """
    view = context.get("view", None)
    # fall back to view attributes if not explicitly passed
    resolved_path = path or getattr(view, "list_path", "")
    resolved_columns = columns or context.get(f"{table_id}_columns", context.get(f"columns", []))
    resolved_page_size = page_size or getattr(view, "page_size", 20)
    resolved_tpl_field = template_field or getattr(view, "template_field", None)
    resolved_tpl_id = template_id or getattr(view, "template_id", None)

    # build config dict
    cfg = {
        "path": resolved_path,
        "columns": resolved_columns,
        "pageSize": resolved_page_size,
    }
    if resolved_tpl_field and resolved_tpl_id:
        cfg["templateField"] = resolved_tpl_field
        cfg["templateId"] = resolved_tpl_id

    html = [
        f'<div id="{table_id}" class="tabulator-widget"></div>',
        "<script>",
            "window.tabulatorDefaults = window.tabulatorDefaults || {};",
            f'window.tabulatorDefaults["{table_id}"] = {json.dumps(cfg)};',
        "</script>"
    ]

    return mark_safe("\n".join(html))
