import json
from django import forms
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string


class QueryBuilderWidget(forms.Widget):
    template_name = "querybuilder/widget.html"

    def __init__(self, *, fields, config_id="default", compact=False, attrs=None):
        super().__init__(attrs)
        self.qb_fields = fields
        self.config_id = config_id
        self.compact = compact

    @property
    def media(self):
        from django.forms.widgets import Media
        return Media(
            css={'all': ['querybuilder/querybuilder.css']},
            js=['querybuilder/querybuilder.js'],
        )

    def value_from_datadict(self, data, files, name):
        raw = data.get(name)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        initial = value if isinstance(value, dict) else None
        ctx.update({
            "config_id": self.config_id,
            "target": f"#{attrs.get('id', f'id_{name}')}",
            "initial": json.dumps(initial) if initial else "",
            "compact": self.compact,
            "setup_script": mark_safe(
                f"<script>window.__QB_CONFIGS__ = window.__QB_CONFIGS__ || {{}};"
                f"window.__QB_CONFIGS__[{json.dumps(self.config_id)}] = {json.dumps(self.qb_fields)};</script>"
            )
        })
        return ctx

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.setdefault('id', f'id_{name}')
        # Render the hidden input that carries the JSON
        hidden = f'<input type="hidden" name="{name}" id="{attrs["id"]}" />'
        html = render_to_string(self.template_name, self.get_context(name, value, attrs))
        return mark_safe(hidden + html)
