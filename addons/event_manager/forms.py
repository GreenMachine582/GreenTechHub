from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import Attendee, Event

User = get_user_model()


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name",
            "short_description",
            "description",
            "date",
            "start_time",
            "end_time",
            "venue_name",
            "venue_address",
            "capacity",
            "rsvp_deadline",
            "allow_public_rsvp",
            "status",
            "cohosts",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "short_description": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "start_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "end_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "venue_name": forms.TextInput(attrs={"class": "form-control"}),
            "venue_address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "capacity": forms.NumberInput(attrs={"class": "form-control"}),
            "rsvp_deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "allow_public_rsvp": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "cohosts": forms.SelectMultiple(
                attrs={"class": "form-select", "size": 4},
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if "cohosts" in self.fields:
            self.fields["cohosts"].queryset = User.objects.filter(is_active=True)

        if not (self.user and getattr(self.user, "is_admin", False)):
            # Remove field entirely for non-admins
            self.fields.pop("cohosts", None)

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("date")
        rsvp_deadline = cleaned.get("rsvp_deadline")

        if date and rsvp_deadline and rsvp_deadline > date:
            self.add_error(
                "rsvp_deadline",
                _("RSVP deadline cannot be after the event date."),
            )
        return cleaned


class PublicRSVPForm(forms.ModelForm):
    """
    Used for public self-registration for an event.
    """
    class Meta:
        model = Attendee
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "attending_count",
            "dietary_requirements",
            "meal_preference",
            "other_notes",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "attending_count": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "dietary_requirements": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "meal_preference": forms.TextInput(attrs={"class": "form-control"}),
            "other_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }


class AttendeeRSVPForm(forms.ModelForm):
    """
    Used when an invited attendee responds via their token link.
    Name/email are fixed; they only update RSVP fields.
    """
    class Meta:
        model = Attendee
        fields = [
            "status",
            "attending_count",
            "dietary_requirements",
            "meal_preference",
            "other_notes",
        ]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "attending_count": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "dietary_requirements": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "meal_preference": forms.TextInput(attrs={"class": "form-control"}),
            "other_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def clean_attending_count(self):
        count = self.cleaned_data["attending_count"]
        status = self.cleaned_data.get("status") or self.instance.status
        if status == Attendee.RSVPStatus.ACCEPTED and count < 1:
            raise forms.ValidationError(
                _("Attending count must be at least 1 if you are attending.")
            )
        return count
