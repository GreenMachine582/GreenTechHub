from django.forms import widgets

class PasswordInput(widgets.PasswordInput):
    template_name = "widgets/bootstrap_password.html"

    def __init__(self, attrs=None, render_value=False):
        default_attrs = {"class": "form-control", "placeholder": "Enter password"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs, render_value)
