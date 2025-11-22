from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class ConfirmTextModalForm(forms.Form):
    confirm_text = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def __init__(self, *args, required_text="DELETE", **kwargs):
        self.required_text = required_text
        super().__init__(*args, **kwargs)
        self.fields["confirm_text"].label = mark_safe(
            _('Type <code>%(text)s</code> to confirm') % {"text": self.required_text}
        )

        self.fields["confirm_text"].widget.attrs.update(
            {
                "data-required-text": self.required_text,
            }
        )

    def clean_confirm_text(self):
        value = (self.cleaned_data.get("confirm_text") or "").strip()
        if value != self.required_text:
            raise forms.ValidationError(
                _('Please type "%(text)s" to confirm.'),
                code="invalid",
                params={"text": self.required_text},
            )
        return value
