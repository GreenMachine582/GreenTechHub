
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

import re


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

    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username",]

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
