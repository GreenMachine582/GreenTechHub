
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from ..base.models import Profile


class SocialAdapter(DefaultSocialAccountAdapter):

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        provider = sociallogin.account.provider
        extra = sociallogin.account.extra_data or {}

        profile, _ = Profile.objects.get_or_create(user=user)

        if not user.profile.avatar_url:
            if provider == "google" and extra.get("picture"):
                profile.avatar_url = extra["picture"]
                profile.avatar_source = "google"
            elif provider == "github" and extra.get("avatar_url"):
                profile.avatar_url = extra["avatar_url"]
                profile.avatar_source = "github"
            profile.save(update_fields=["avatar_url", "avatar_source"])

        return user
