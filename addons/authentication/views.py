
from allauth.socialaccount.models import SocialAccount, SocialToken
from bootstrap_modal_forms.generic import BSModalFormView
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (authenticate, login, logout, get_user_model, update_session_auth_hash,
                                 REDIRECT_FIELD_NAME)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, resolve_url, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import FormView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import UserRegistrationForm, SetPasswordModalForm, ChangePasswordModalForm, ResetPasswordModalForm
from .models import GroupProfile
from ..base.views import LoginRequiredView
from ..modal_forms.mixins import ModalFormMixin

User = get_user_model()

class UserRegistrationFormView(FormView):
    form_class = UserRegistrationForm
    template_name = "users-register.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        new_user = form.save()
        login(self.request, new_user)  # Sign user in after registration
        messages.success(self.request, "Your account has been created successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        error_message = "<p>Failed to register. Please correct the errors below: </p><ul>"
        for field, errors in form.errors.items():
            for error in errors:
                # Label the error with the field name if available
                field_name = form.fields[field].label if field in form.fields else "Error"
                error_message += f"<li><strong>{escape(field_name)}:</strong> {escape(error)}</li>"
        error_message += "</ul>"
        form.errors.clear()
        messages.error(self.request, error_message)
        return super().form_invalid(form)


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


class DeleteAccountView(ModalFormMixin, LoginRequiredView):
    """
    GET (AJAX): returns the confirmation modal HTML.
    POST: validates confirm_text/password, logs out, deletes account, redirects.

    Uses: modal_forms/confirm_modal.html
    """

    # modal config
    confirm_template_name = "modal_forms/confirm_modal.html"
    confirm_title = "Delete Account"
    confirm_message = (
        "This will permanently delete your account, this action cannot be undone. You will be logged out immediately."
    )
    submit_label = "Delete my account"
    submit_class = "btn-danger"
    header_class = "bg-danger text-white"
    icon = "fas fa-triangle-exclamation"

    required_text = "DELETE"

    success_url = "/"  # or reverse_lazy("home")
    redirect_url = "users-profile"

    def _wouldRemoveLastSuperuser(self, u: User) -> bool:
        return u.is_superuser and User.objects.filter(is_superuser=True).exclude(pk=u.pk).count() == 0

    # ---------- GET: return modal HTML (AJAX only) ----------
    def get(self, request, *args, **kwargs):
        context = {
            "action_url": request.path,
            "modal_id": "deleteAccountModal",
            "title": self.confirm_title,
            "message": self.confirm_message,
            "submit_label": self.submit_label,
            "submit_class": self.submit_class,
            "header_class": self.header_class,
            "icon": self.icon,
            "require_text": self.required_text,
        }
        return render(request, self.confirm_template_name, context)

    # ---------- POST: perform deletion ----------
    def post(self, request, *args, **kwargs):
        user = request.user
        confirm_text = (request.POST.get("confirm_text") or "").strip()
        if confirm_text != self.required_text:
            messages.error(request, _(f'Please type "{self.required_text}" to confirm.'))
            return redirect("users-profile")

        # Prevent removing last superuser
        if self._wouldRemoveLastSuperuser(user):
            messages.error(
                request, _("You are the last superuser. Promote another admin before deleting this account.")
            )
            return redirect("users-profile")
        logout(request)

        user.delete()
        messages.success(request, _("Your account has been deleted."))
        return redirect(resolve_url(self.success_url))


class ChangePasswordModalView(ModalFormMixin, LoginRequiredMixin, BSModalFormView):
    template_name = "account/modals/password_change.html"
    form_class = ChangePasswordModalForm
    success_message = "Password changed successfully."
    extra_context = {
        "action_url": reverse_lazy("password-change-modal"),
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        nxt = self.request.GET.get("next") or self.request.POST.get("next")
        return nxt or super().get_success_url()

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ResetPasswordModalView(ModalFormMixin, LoginRequiredMixin, BSModalFormView):
    template_name = "account/modals/password_reset.html"
    form_class = ResetPasswordModalForm
    success_message = "Password reset email sent to {email}."
    extra_context = {
        "action_url": reverse_lazy("password-reset-modal"),
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("initial", {})
        kwargs["initial"]["email"] = self.request.user.email
        return kwargs

    def form_valid(self, form):
        form.save(self.request)
        return super().form_valid(form)
