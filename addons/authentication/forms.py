
import re

from allauth.account.forms import (
    SignupForm as _SignupForm,
    ChangePasswordForm as _ChangePasswordForm,
    ResetPasswordForm as _ResetPasswordForm,
    ResetPasswordKeyForm as _ResetPasswordKeyForm,
    SetPasswordForm as _SetPasswordForm,
)
from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..base import widgets

User = get_user_model()


def validate_password_strength(value):
    """
    Custom password validation logic:
    - At least 8 characters long
    - At least 1 uppercase, lowercase, digit, special character
    """
    if len(value) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", value):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", value):
        raise ValidationError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
        raise ValidationError("Password must contain at least one special character.")


class SignupForm(_SignupForm):

    username_validator = UnicodeUsernameValidator()

    first_name = forms.CharField(
        label=_("First"), max_length=150, required=False,
        widget=widgets.TextInput(attrs={"placeholder": "Joe"}),
    )
    last_name = forms.CharField(
        label=_("Last"), max_length=150, required=False,
        widget=widgets.TextInput(attrs={"placeholder": "Doe"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "username" in self.fields:
            self.fields["username"].widget = widgets.UsernameInput(
                attrs={"placeholder": "JoeDoe123", "autocomplete": "username"},
                prepend="@",
            )
            self.fields["username"].validators.append(self.username_validator)
            self.fields["username"].help_text = _(
                "Required. 150 characters or fewer. "
                "Letters, digits and @/./+/-/_ only."
            )

        if "email" in self.fields:
            self.fields["email"].widget = widgets.EmailInput(
                attrs={"placeholder": "Joe.Doe@gmail.com"}
            )

        if "password1" in self.fields:
            self.fields["password1"].widget = widgets.CustomPasswordInput(
                attrs={"autocomplete": "new-password", "placeholder": "Jo4Do3!&"})
            self.fields["password1"].help_text = ""
        if "password2" in self.fields:
            self.fields["password2"].widget = widgets.PasswordInput(
                attrs={"autocomplete": "new-password", "placeholder": "Jo4Do3!&"})

    def clean_password1(self):
        if password := self.cleaned_data.get("password1"):
            validate_password_strength(password)
        return password

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.save(update_fields=["first_name", "last_name"])
        return user


class SetPasswordModalForm(BSModalForm, _SetPasswordForm):
    class Meta:
        fields = ("password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget = widgets.CustomPasswordInput(attrs={
            "autocomplete": "new-password",
            "placeholder": _("Jo4Do3!&"),
        })
        self.fields["password1"].help_text = ""

class ChangePasswordModalForm(BSModalForm, _ChangePasswordForm):
    class Meta:
        fields = ("oldpassword", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_fields = ["oldpassword", "password1", "password2"]
        for f in required_fields:
            if f in self.fields:
                self.fields[f].required = True
        if "password1" in self.fields:
            self.fields["password1"].widget = widgets.CustomPasswordInput(attrs={
                "autocomplete": "new-password",
                "placeholder": _("New password"),
            })
            self.fields["password1"].help_text = ""


class ResetPasswordModalForm(BSModalForm, _ResetPasswordForm):
    class Meta:
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["email"].widget = forms.HiddenInput()


class ResetPasswordForm(_ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "new_password1" in self.fields:
            self.fields["new_password1"].widget = widgets.CustomPasswordInput(attrs={
                "autocomplete": "new-password",
                "placeholder": "New Password",
            })
        if "email" in self.fields:
            self.fields["email"].widget = widgets.EmailInput(attrs={
                "placeholder": "Joe.Doe@gmail.com"})


class ResetPasswordKeyForm(_ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget = widgets.CustomPasswordInput(attrs={
            "autocomplete": "new-password",
            "placeholder": "Jo4Do3!&",
        })
        self.fields["password1"].help_text = ""
        # self.fields["password2"].widget = widgets.PasswordInput(attrs={
        #     "autocomplete": "new-password",
        #     "placeholder": "Repeat Password",
        # })


class SetPasswordKeyForm(_SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget = widgets.CustomPasswordInput(attrs={
            "autocomplete": "new-password",
            "placeholder": "New Password",
        })