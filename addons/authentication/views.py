
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.html import escape
from django.views.generic import FormView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import UserRegistrationForm
from .models import GroupProfile

# Create your views here.

class UserRegistrationFormView(FormView):
    form_class = UserRegistrationForm
    template_name = "users-register.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        new_user = form.save()
        login(self.request, new_user)  # Sign user in after registration
        messages.success(self.request, "Your account has been created successfully!")
        return super().form_valid(new_user)

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

            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login")
    return render(request, 'users-login.html')


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
