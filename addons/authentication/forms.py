
import re

from allauth.account.forms import (ChangePasswordForm as _ChangePasswordForm, ResetPasswordForm as _ResetPasswordForm,
                                   ResetPasswordKeyForm as _ResetPasswordKeyForm, SetPasswordForm as _SetPasswordForm)
from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User, UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..base import widgets


def validate_password_strength(value):
    """
    Custom password validation logic:
    - At least 8 characters long
    - At least 1 uppercase, lowercase, digit, special character
    - Cannot contain the username
    """
    if len(value) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', value):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', value):
        raise ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r'\d', value):
        raise ValidationError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
        raise ValidationError("Password must contain at least one special character.")


class UserRegistrationForm(forms.ModelForm):

    username_validator = UnicodeUsernameValidator()

    username = forms.CharField(
        label=_("Username"),
        max_length=150,
        widget=widgets.TextInput(attrs={"placeholder": "JoeDoe123"}, prepend="@"),
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    first_name = forms.CharField(
        label=_("First Name"), max_length=150,
        widget=widgets.TextInput(attrs={"placeholder": "Joe"}),
    )
    last_name = forms.CharField(
        label=_("Last Name"), max_length=150,
        widget=widgets.TextInput(attrs={"placeholder": "Doe"}),
    )
    email = forms.EmailField(
        label=_("Email"),
        widget=widgets.EmailInput(attrs={"placeholder": "Joe.Doe@gmail.com"}),
    )

    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=widgets.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Jo4Do3!&"}),
        help_text=password_validation.password_validators_help_text_html(),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username", "password"]

    def save(self, commit=True):
        """Save user with hashed password."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Hash password
        if commit:
            user.save()
        return user

    def clean_username(self):
        """Reject usernames that differ only in case."""
        username = self.cleaned_data.get("username")
        if not username or not self._meta.model.objects.filter(username__iexact=username).exists():
            return username

        self._update_errors(ValidationError({
            "username": self.instance.unique_error_message(self._meta.model, ["username"])
        }))

    def clean_password(self):
        password = self.cleaned_data.get("password")
        try:
            validate_password_strength(password)
        except ValidationError:
            self.add_error("password",
                           ValidationError("Must be 8+ characters with an uppercase, lowercase, number, and a special "
                                           "character."))
        return password


class SetPasswordModalForm(BSModalForm, _SetPasswordForm):
    class Meta:
        fields = ("new_password1", "new_password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget = widgets.PasswordInput(attrs={
            "autocomplete": "new-password",
            "placeholder": _("Jo4Do3!&"),
        })
        self.fields["new_password1"].help_text = (
            self.fields["new_password1"].help_text
            or password_validation.password_validators_help_text_html()
        )

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
            self.fields["password1"].widget = widgets.PasswordInput(attrs={
                "autocomplete": "new-password",
                "placeholder": _("New password"),
            })
            self.fields["password1"].help_text = ""