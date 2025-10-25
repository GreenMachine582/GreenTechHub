import mimetypes

from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect
from django.utils.http import http_date
from django.utils.timezone import now

from .forms import ProfileForm
from .models import Profile


def home(request):
    return render(request, 'index.html')


# def user_profile(request):
#     if not request.user.is_authenticated:
#         response = redirect("home")
#         messages.error(request, "Session has expired.")
#         return response
#     return render(request, 'users-profile.html')


@login_required
def serve_my_avatar(request):
    try:
        profile = Profile.objects.select_related("user").get(user=request.user)
    except Profile.DoesNotExist:
        raise Http404()

    if not profile.avatar:
        raise Http404()

    f = profile.avatar.open("rb")
    ctype, _ = mimetypes.guess_type(profile.avatar.name)
    resp = FileResponse(f, content_type=ctype or "application/octet-stream")
    resp["Cache-Control"] = "private, max-age=300"
    resp["Last-Modified"] = http_date(now().timestamp())
    return resp


@login_required
def user_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        msg = ""
        if "clear_avatar" in request.POST:
            msg = "Uploaded avatar removed. Using provider avatar if available."
        if "refresh_from_provider" in request.POST:
            msg = "Provider avatar refreshed."

        if msg:
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar = None
            profile.avatar_source = "google" if "googleusercontent" in (profile.avatar_url or "") else (
                "github" if profile.avatar_url else "none"
            )
            profile.save(update_fields=["avatar", "avatar_source"])
            messages.success(request, msg)
            return redirect("users-profile")

        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("users-profile")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileForm(instance=profile)

    connected = list(SocialAccount.objects.filter(user=request.user))
    return render(request, "users-profile.html", {
        "form": form,
        "connected_accounts": connected,
    })

