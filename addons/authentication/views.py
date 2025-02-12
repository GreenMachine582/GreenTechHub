
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

# Create your views here.

def user_register(request):
    if request.method == 'POST':
        kwargs = dict(request.POST.items())
        kwargs.pop('csrfmiddlewaretoken', None)
        try:
            new_user = User.objects.create_user(**kwargs)
            messages.success(request, "Your account has been created successfully!")
            return redirect("home")
        except Exception as e:
            messages.error(request, "There was an error in your form. Please correct it and try again.")
    return render(request, 'users-register.html')


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
    return redirect("home")
