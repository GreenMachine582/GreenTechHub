from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'addons.base'

    def ready(self):
        from . import signals
        from django.forms import widgets as W

        def add_class(attrs: dict, extra: str):
            if not extra:
                return attrs
            existing = attrs.get("class", "")
            existing_set = set(existing.split()) if existing else set()
            for c in extra.split():
                if c and c not in existing_set:
                    existing_set.add(c)
            if existing_set:
                attrs["class"] = " ".join(sorted(existing_set, key=lambda x: x))
            return attrs

        def wrap_get_context(widget_cls, class_resolver):
            orig = widget_cls.get_context

            def get_context(self, name, value, attrs):
                attrs = attrs or {}

                # Opt-out per-field or per-widget
                if attrs.pop("bs_skip", False) or getattr(self, "bs_skip", False):
                    return orig(self, name, value, attrs)

                # Inject base class
                add_class(attrs, class_resolver(self))

                # Optional size helpers: bs_size="sm"|"lg"
                size = attrs.pop("bs_size", None)
                cls_str = attrs.get("class", "")
                if size in ("sm", "lg"):
                    if "form-select" in cls_str:
                        add_class(attrs, f"form-select-{size}")
                    elif "form-control" in cls_str:
                        add_class(attrs, f"form-control-{size}")

                return orig(self, name, value, attrs)

            widget_cls.get_context = get_context

        # Resolvers per widget family
        control         = lambda _: "form-control"
        control_select  = lambda _: "form-select"
        check_input     = lambda _: "form-check-input"
        file_control    = lambda _: "form-control"

        # Text-like
        for cls in (W.TextInput, W.EmailInput, W.URLInput, W.PasswordInput,
                    W.NumberInput, W.Textarea, W.DateInput, W.TimeInput,
                    W.DateTimeInput, W.SearchInput):
            wrap_get_context(cls, control)

        # Selects
        for cls in (W.Select, W.SelectMultiple):
            wrap_get_context(cls, control_select)

        # Check/radio
        wrap_get_context(W.CheckboxInput, check_input)
        wrap_get_context(W.RadioSelect,  check_input)

        # Files & others
        for cls in (W.FileInput, W.ClearableFileInput):
            wrap_get_context(cls, file_control)