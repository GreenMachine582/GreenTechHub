
import json

from django import template
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.template.loader import render_to_string

register = template.Library()


def infer_qb_fields_from_columns(columns):
    type_map = {
        "tickCross": "boolean",
        "string": "string",
        "number": "integer",
    }
    qb_fields = []

    for col in columns:
        if "field" not in col or "title" not in col or col["field"] in ("actions", "action", "edit", "delete"):
            continue  # skip non-data or action columns

        field_type = "string"  # default type

        # Infer from formatter or sorter
        if col.get("formatter") in type_map:
            field_type = type_map[col["formatter"]]
        elif col.get("editor") in type_map:
            field_type = type_map[col["editor"]]
        elif col.get("sorter") in type_map:
            field_type = type_map[col["sorter"]]

        qb_fields.append({
            "name": col["field"],
            "label": col["title"],
            "type": field_type,
        })

    return qb_fields


@register.simple_tag(takes_context=True)
def render_tabulator(context, path=None, table_id="records-table", columns=None, page_size=0,
                     filters=None, filter_form=None, include_qb=True, qb_fields=None):
    """
    Renders an empty <div> for Tabulator and optionally includes QueryBuilder.
    """
    view = context.get("view", None)
    # fall back to view attributes if not explicitly passed
    resolved_path = path or getattr(view, "list_path", "")
    resolved_columns = columns or context.get(f"{table_id}_columns", context.get("columns", []))
    resolved_template_columns = context.get(f"{table_id}_template_columns", context.get("template_columns", []))
    resolved_page_size = page_size or getattr(view, "page_size", 20)

    resolved_filters = (
        filters
        or getattr(view, "list_filters", None)
        or context.get(f"{table_id}_filters", context.get("filters", None))
    )
    resolved_filter_form = (
        filter_form
        or getattr(view, "filter_form", None)
        or context.get(f"{table_id}_filter_form", context.get("filter_form", None))
    )

    resolved_qb_fields = qb_fields or context.get("qb_fields") or infer_qb_fields_from_columns(resolved_columns)
    resolved_qb_config_id = slugify(table_id)

    cfg = {
        "path": resolved_path,
        "columns": resolved_columns,
        "pageSize": resolved_page_size,
        "templateColumns": resolved_template_columns,
        "showSummary": True,
        "includeQB": include_qb,
    }
    if resolved_filters is not None:
        # allow dict OR querystring string
        cfg["filters"] = resolved_filters
    if resolved_filter_form:
        cfg["filterForm"] = resolved_filter_form

    data_attrs = []
    if isinstance(resolved_filters, str):
        # querystring style can be placed as a data-attribute
        data_attrs.append(f'data-filters="{resolved_filters}"')
    if resolved_filter_form:
        data_attrs.append(f'data-filter-form="{resolved_filter_form}"')

    html = []

    if include_qb:
        qb_html = render_to_string("querybuilder/widget.html", {
            "config_id": resolved_qb_config_id,
            "fields_json": mark_safe(json.dumps(resolved_qb_fields)),
            "initial": json.dumps(resolved_filters) if isinstance(resolved_filters, dict) else "",
            "compact": True,
            "collapsed": False,
            "auto_input": True,
            "input_id": f"qb-{resolved_qb_config_id}-filters",
            "name": "filters",
            "target": f"#qb-{resolved_qb_config_id}-filters"
        }, request=context.get("request"))
        html.append(qb_html)

    html.extend([
        f'<div id="{table_id}-summary" class="tabulator-summary small text-muted mt-2"></div>',
        f'<div id="{table_id}" class="tabulator-widget" {" ".join(data_attrs)}></div>',
        "<script>",
        "  window.tabulatorDefaults = window.tabulatorDefaults || {};",
        f'  window.tabulatorDefaults["{table_id}"] = {json.dumps(cfg)};',
        "</script>",
    ])

    return mark_safe("\n".join(html))
