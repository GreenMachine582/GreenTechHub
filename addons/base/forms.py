
from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["avatar"]
        widgets = {
            "avatar": forms.FileInput(attrs={
                "accept": "image/*",
                "class": "form-control",
            }),
        }

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.cleaned_data.get("avatar"):
            profile.avatar_source = "upload"
        if commit:
            profile.save()
        return profile
