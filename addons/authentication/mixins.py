
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin as BaseLoginRequiredMixin


class LoginRequiredMixin(BaseLoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Session has expired.")
        return super().dispatch(request, *args, **kwargs)
