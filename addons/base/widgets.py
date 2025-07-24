from django.forms import widgets


class BootstrapWidgetMixin:
    """
    Generic mixin to inject a default Bootstrap class into any widget.
    Child classes should set `default_class`.
    """
    default_class = ""

    def __init__(self, attrs=None, **kwargs):
        attrs = attrs or {}
        # merge any existing classes with our default
        existing = attrs.get("class", "")
        classes = f"{existing} {self.default_class}".strip()
        attrs["class"] = classes
        super().__init__(attrs, **kwargs)


class BootstrapCheckboxMixin(BootstrapWidgetMixin):
    default_class = "form-check-input"
    template_name = "widgets/bootstrap_checkbox.html"

    def __init__(self, attrs=None, switch=False, **kwargs):
        """
        :param switch: if True, adds the .form-switch wrapper class
        """
        super().__init__(attrs=attrs, **kwargs)
        self.switch = switch

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["widget"]["switch"] = self.switch
        return ctx



class BootstrapInputMixin(BootstrapWidgetMixin):
    """A mixin to extend input widgets with Bootstrap 5 support."""
    default_class = "form-control"

    def __init__(self, attrs=None, placeholder=None, prepend=None, append=None, **kwargs):
        super().__init__(attrs=attrs, **kwargs)
        if placeholder:
            self.attrs["placeholder"] = placeholder
        self.prepend = prepend
        self.append = append

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"].update({
            "prepend": self.prepend,
            "append": self.append
        })
        return context


class TextInput(BootstrapInputMixin, widgets.TextInput):
    """Bootstrap-styled Text Input."""
    template_name = "widgets/bootstrap_input.html"


class NumberInput(BootstrapInputMixin, widgets.NumberInput):
    """Bootstrap-styled Number Input."""
    template_name = "widgets/bootstrap_input.html"


class EmailInput(BootstrapInputMixin, widgets.EmailInput):
    """Bootstrap-styled Email Input."""
    template_name = "widgets/bootstrap_input.html"


class URLInput(BootstrapInputMixin, widgets.URLInput):
    """Bootstrap-styled URL Input."""
    template_name = "widgets/bootstrap_input.html"


class PasswordInput(BootstrapInputMixin, widgets.PasswordInput):
    """
    Bootstrap 5 styled password input with optional visibility toggle.
    """
    template_name = "widgets/bootstrap_password.html"

    def __init__(self, attrs=None, render_value=False, placeholder="Enter password", **kwargs):
        """
        :param attrs: HTML attributes
        :param render_value: Whether to render the password value
        :param placeholder: Placeholder text
        """
        super().__init__(attrs=attrs, placeholder=placeholder, **kwargs)
        self.render_value = render_value


class CheckboxInput(BootstrapCheckboxMixin, widgets.CheckboxInput):
    """A normal Bootstrap checkbox."""


class SwitchInput(BootstrapCheckboxMixin, widgets.CheckboxInput):
    """A Bootstrap switch (toggle)."""
    def __init__(self, attrs=None, **kwargs):
        # always renders as a .form-switch
        super().__init__(attrs=attrs, switch=True, **kwargs)

