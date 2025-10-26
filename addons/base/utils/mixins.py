
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlsplit


class AjaxAwareLoginRequiredMixin:
    """
    For CBVs: if unauthenticated…
      - normal request -> redirect_to_login(?next=…)
      - AJAX request   -> JSON 401 {redirect: "<login?next=...>"}
      - HTMX request   -> 401 with HX-Redirect header
    Also pushes a 'Session has expired.' message.
    """
    login_url = None
    redirect_field_name = REDIRECT_FIELD_NAME
    login_message = "Session has expired."

    def get_login_url(self):
        return resolve_url(self.login_url or settings.LOGIN_URL)

    def _as_path_query(self, url: str) -> str:
        p = urlsplit(url)
        path = p.path or "/"
        return f"{path}?{p.query}" if p.query else path

    def _parent_next(self, request):
        """
        Prefer the page the user was on before hitting the modal endpoint.
        Precedence:
          1) HTMX header: HX-Current-URL
          2) Referer header
        Only if same-origin with LOGIN_URL host.
        """
        candidate = (
            request.headers.get("HX-Current-URL")
            or request.META.get("HTTP_REFERER")
        )
        if not candidate:
            return None
        if not url_has_allowed_host_and_scheme(
                url=candidate,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
        ):
            return None
        return self._as_path_query(candidate)

    def _unauthenticated_response(self, request):
        messages.error(request, self.login_message)

        is_htmx = request.headers.get("HX-Request") == "true"
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        default_next = request.get_full_path()
        next_target = self._parent_next(request) if (is_htmx or is_ajax) else default_next
        next_target = next_target or default_next

        login_resp = redirect_to_login(next_target, self.get_login_url(), self.redirect_field_name)
        target = login_resp["Location"]

        # For HTMX/AJAX, return 401 and tell client to navigate
        if is_htmx:
            resp = HttpResponse(status=401)
            resp["HX-Redirect"] = target
            return resp

        if is_ajax:
            return JsonResponse({"redirect": target}, status=401)

        # Plain request: normal redirect
        return login_resp

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        return self._unauthenticated_response(request)


class AjaxOnlyMixin:
    """
    Mixin that restricts access to AJAX (or HTMX) requests only.

    Features:
      • Restricts specific HTTP methods (default: GET)
      • Supports both 'X-Requested-With: XMLHttpRequest' and 'HX-Request: true'
      • Configurable fallback: redirect, 405, or JSON error

    Example:
        class MyModalView(AjaxOnlyMixin, View):
            ajax_methods = ["GET"]              # default
            redirect_url = "home"               # optional
            ajax_response_type = "redirect"     # redirect | 405 | json
    """

    ajax_methods = ["GET"]            # methods that must be AJAX-only
    redirect_url = None               # e.g., "home" or "users-profile"
    ajax_response_type = "redirect"   # "redirect", "405", or "json"

    def is_ajax_request(self, request):
        """Return True if the request came via AJAX or HTMX."""
        return (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.headers.get("HX-Request") == "true"
        )

    def handle_non_ajax(self, request):
        """Handle non-AJAX requests depending on mixin settings."""
        if self.ajax_response_type == "405":
            return HttpResponseNotAllowed(self.ajax_methods)

        if self.ajax_response_type == "json":
            return JsonResponse(
                {"error": "This endpoint only accepts AJAX requests."},
                status=400,
            )

        # Default behavior: redirect to a configured or fallback page
        target = self.redirect_url or "home"
        return redirect(target)

    def dispatch(self, request, *args, **kwargs):
        if request.method in self.ajax_methods and not self.is_ajax_request(request):
            return self.handle_non_ajax(request)
        return super().dispatch(request, *args, **kwargs)
