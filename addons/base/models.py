
from __future__ import annotations

import os
import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property

from .storage import private_storage


def profile_avatar_path(instance, filename):
    # /media/avatars/u<id>/<uuid>.<ext>
    ext = os.path.splitext(filename)[1].lower()  # includes dot
    return f"avatars/u{instance.user_id}/{uuid.uuid4().hex}{ext}"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    avatar = models.ImageField(
        storage=private_storage,
        upload_to=profile_avatar_path,
        blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
    )
    avatar_url = models.URLField(blank=True)
    AVATAR_SRC_CHOICES = [
        ("upload", "Upload"),
        ("google", "Google"),
        ("github", "GitHub"),
        ("none", "None"),
    ]
    avatar_source = models.CharField(max_length=16, choices=AVATAR_SRC_CHOICES, default="none", blank=True)

    @cached_property
    def has_upload(self) -> bool:
        return bool(self.avatar)

    def _avatar_version(self) -> str:
        """Cache-buster for browsers; safe if storage doesn't expose stat()."""
        try:
            path = self.avatar.path  # works for FileSystemStorage
            return str(int(os.path.getmtime(path)))
        except Exception:
            return ""

    @cached_property
    def effective_avatar_url(self) -> str | None:
        """URL suitable for <img src=...>. Uses private route if upload exists; else provider URL."""
        if self.has_upload:
            url = reverse("serve-my-avatar")
            v = self._avatar_version()
            return f"{url}?v={v}" if v else url
        if self.avatar:
            return self.avatar.url
        if self.avatar_url:
            return self.avatar_url
        return None
