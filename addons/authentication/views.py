
from allauth.socialaccount.models import SocialAccount, SocialToken
from bootstrap_modal_forms.generic import BSModalFormView
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model, REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
# from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import SetPasswordModalForm, ChangePasswordModalForm, ResetPasswordModalForm
from .models import GroupProfile
from ..base.views import LoginRequiredView
from ..modal_forms.views import FormModalView, DeleteConfirmModalView

User = get_user_model()


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = bool(request.POST.get('remember_me'))
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            if remember_me:
                request.session.set_expiry(getattr(settings, "SESSION_REMEMBER_ME_SECS", 60 * 60 * 24 * 30))  # 30 days
            else:
                request.session.set_expiry(60 * 60)  # 1 hr

            next_url = request.POST.get(REDIRECT_FIELD_NAME) or request.GET.get(REDIRECT_FIELD_NAME)
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("home")
        messages.error(request, "Invalid username or password.")
        return redirect("login")

    # Ensure template includes a hidden 'next' field if present
    ctx = {REDIRECT_FIELD_NAME: request.GET.get(REDIRECT_FIELD_NAME, "")}
    return render(request, 'users-login.html', ctx)


def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def access_check(request):
    user = request.user

    required_group = request.data.get('group', '')
    required_groups = set(request.data.get('groups', '').split(',')) - {''}

    if not required_groups:
        if not required_group:
            return Response({'allowed': False})
        required_groups = {required_group}

    user_group_ids = set(user.groups.values_list('id', flat=True))

    for group_code in required_groups:
        group = GroupProfile.get_group_by_code_name(group_code)
        if group and group.id in user_group_ids:
            return Response({'allowed': True})

    return Response({'allowed': False})


class RemoveConnectionConfirmView(LoginRequiredView):
    template_name = "modal_forms/confirm_modal.html"
    redirect_url = "users-profile"

    def get(self, request, pk):
        # AJAX-only modal body
        acc = get_object_or_404(SocialAccount, pk=pk, user=request.user)
        ctx = {
            "modal_id": "removeConnectionModal",
            "action_url": reverse("users-remove-connection", args=[acc.pk]),
            "title": "Remove Connected Account",
            "message": f"Disconnect your {acc.provider.title()} account?",
            "submit_label": "Remove",
            "submit_class": "btn-danger",
            "header_class": "bg-danger text-white",
            "icon": "fas fa-link-slash",
        }
        return render(request, self.template_name, ctx)


@require_POST
@login_required
def remove_connection(request, pk: int):
    acc = get_object_or_404(SocialAccount, pk=pk, user=request.user)

    # Lockout safety: if user has no password and only one connection, block removal
    only_connection = request.user.socialaccount_set.count() == 1
    if only_connection and not request.user.has_usable_password():
        messages.error(
            request,
            "You don’t have a password set. Add another social account or set a password before removing your only login method.",
        )
        return redirect("users-profile")

    # Optional: remove any stored OAuth tokens for this account
    SocialToken.objects.filter(account=acc).delete()

    acc.delete()

    messages.success(request, "Connected account removed.")
    return redirect("users-profile")


class DeleteAccountModalView(DeleteConfirmModalView):
    """
    Confirm deletion of the current user's account.
    """

    modal_title = _("Delete Account")
    modal_message = (
        "This will permanently delete your account, this action cannot be undone. You will be logged out immediately."
    )
    submit_label = _("Delete account")

    def _wouldRemoveLastSuperuser(self, u: User) -> bool:
        return u.is_superuser and User.objects.filter(is_superuser=True).exclude(pk=u.pk).count() == 0

    def perform_action(self, form):
        user = self.request.user

        # Prevent removing last superuser
        if self._wouldRemoveLastSuperuser(user):
            form.add_error(
                None,
                _(
                    "You are the last superuser. "
                    "Promote another admin before deleting this account."
                ),
            )
            # This will now stay in the modal and show the error
            return

        logout(self.request)
        user.delete()
        messages.success(self.request, _("Your account has been deleted."))


class ChangePasswordModalView(FormModalView):
    template_name = "account/modals/password_change.html"
    form_class = ChangePasswordModalForm
    success_message = "Password changed successfully."
    modal_title = _("Change Password")
    modal_icon = "fas fa-key"
    submit_label = _("Change password")
    extra_context = {
        "action_url": reverse_lazy("password-change-modal"),
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def perform_action(self, form):
        form.save()


class ResetPasswordModalView(FormModalView):
    form_class = ResetPasswordModalForm
    success_message = "Password reset email sent to {email}."
    modal_title = _("Send Password Reset Email")
    modal_icon = "fas fa-envelope"
    submit_label = _("Send email")
    extra_context = {
        "action_url": reverse_lazy("password-reset-modal"),
        "message_html": _(
            "We will email a password reset link to <strong>{email}</strong>."
        ),
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("initial", {})
        kwargs["initial"]["email"] = self.request.user.email
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        email = self.request.user.email
        ctx["message_html"] = ctx["message_html"].format(email=escape(email))
        return ctx

    def perform_action(self, form):
        form.save(self.request)


class SetPasswordModalView(FormModalView):
    form_class = SetPasswordModalForm
    success_message = "Password set successfully."
    modal_title = _("Set Password")
    modal_icon = "fas fa-key"
    submit_label = _("Set password")

    extra_context = {
        "action_url": reverse_lazy("password-set-modal"),
    }

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def perform_action(self, form):
        form.save()
