
from django.contrib import messages
from django.shortcuts import render, redirect

# Create your views here.

def home(request):
    return render(request, 'index.html')


def user_profile(request):
    if not request.user.is_authenticated:
        response = redirect("home")
        messages.error(request, "Session has expired.")
        return response
    return render(request, 'users-profile.html')
