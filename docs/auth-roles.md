# Authentication & Authorization

## Custom User Model

`AUTH_USER_MODEL = "authentication.User"` is set in `server/settings.py`.

**Always** import the user model via:
```python
from django.contrib.auth import get_user_model
User = get_user_model()

# or in ForeignKeys/signals:
from django.conf import settings
models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
```

Never use `from django.contrib.auth.models import User` — it returns the wrong model.

---

## Role System Architecture

Three-layer design on top of Django's built-in Group/Permission system:

```
django.contrib.auth.Group      ← standard permission container
         │
         │  OneToOne
         ▼
    GroupProfile               ← adds stable slug (code_name) and description
         │
         │  M2M (via Role.groups)
         ▼
        Role                   ← named bundle of Groups + Permissions
         │
         │  FK (nullable)
         ▼
        User                   ← has a Role; also has direct groups
```

**Key concepts:**
- A `GroupProfile.code_name` is the stable string identifier used in access checks (auto-slugged from Group name: `"Admin Group"` → `"admin_group"`)
- A `Role` bundles many Groups; assigning a Role to a User grants all the Role's Groups
- The `"Admin"` Role is special — automatically contains all Groups and is auto-assigned to superusers

---

## Access Checking

### In Python code

```python
user.hasGroups("admin_group")                   # single group check
user.hasGroups("admin_group", "pyfinbot_user")  # OR — True if user has either
```

Internally, `hasGroups` checks:
1. The user's direct `user.groups` (Django M2M)
2. The user's `user.role.groups` (groups inherited via Role)

**Never** use `user.groups.filter(name=...).exists()` — it misses role-inherited groups.

### Via REST API

External services (e.g., microservices) can check access via:
```
POST /api/access-check/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{"group": "admin_group"}
```
Returns `{"allowed": true}` or `{"allowed": false}`.

Multiple groups (OR logic): `{"groups": "admin_group,pyfinbot_user"}`

---

## Creating Groups and Roles

Always use the factory method to create Groups — it ensures the GroupProfile is created atomically:

```python
from addons.authentication.models import GroupProfile

# Creates Group + GroupProfile idempotently
profile = GroupProfile.createGroupAndProfile("My Feature Users", "Can access feature X")
group = profile.group  # the django Group
```

A new Group created this way will automatically be added to the Admin Role via the `add_new_group_to_admin_role` signal.

**Do not** use bare `Group.objects.create()` — a GroupProfile will be created by signal, but the description won't be set and the code_name may collide.

---

## Protecting Views

### Class-Based Views

Use `LoginRequiredMixin` from `addons.authentication.mixins`:

```python
from addons.authentication.mixins import LoginRequiredMixin

class MyView(LoginRequiredMixin, TemplateView):
    template_name = "myapp/thing.html"
```

This mixin is AJAX/HTMX-aware (`AjaxAwareLoginRequiredMixin` from `addons.base.utils.mixins`):
- Standard request → redirect to `settings.LOGIN_URL` with `next=` parameter
- AJAX request → returns `{"redirect": "/accounts/login/?next=..."}` with HTTP 401
- HTMX request → returns HTTP 401 with `HX-Redirect` header

### Function-Based Views

```python
from django.contrib.auth.decorators import login_required

@login_required
def my_view(request):
    ...
```

### Group-Based Access

No built-in mixin exists yet — check in the view:
```python
class MyView(LoginRequiredMixin, TemplateView):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.hasGroups("pyfinbot_user"):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```

---

## django-allauth Configuration

**Settings in `server/settings.py`:**

| Setting | Value |
|---|---|
| `ACCOUNT_LOGIN_METHODS` | `{"email", "username"}` — both work |
| `ACCOUNT_SIGNUP_FIELDS` | `["email*", "username*", "password1*", "password2*"]` |
| `ACCOUNT_EMAIL_VERIFICATION` | `"mandatory"` — email must be confirmed before login |
| `ACCOUNT_EMAIL_SUBJECT_PREFIX` | `"[GreenTechHub] "` |
| `SOCIALACCOUNT_AUTO_SIGNUP` | `True` — no extra form on first social login |
| `SOCIALACCOUNT_LOGIN_ON_GET` | `True` — OAuth redirect doesn't require a POST first |
| `SOCIALACCOUNT_EMAIL_VERIFICATION` | `"none"` — social accounts skip email verification |
| `SOCIALACCOUNT_ADAPTER` | `addons.authentication.adapters.SocialAdapter` |

**Custom allauth forms** (wired via `ACCOUNT_FORMS`):

| Hook | Class |
|---|---|
| `signup` | `addons.authentication.forms.SignupForm` |
| `change_password` | `addons.authentication.forms.ChangePasswordForm` |
| `reset_password` | `addons.authentication.forms.ResetPasswordForm` |
| `reset_password_from_key` | `addons.authentication.forms.ResetPasswordKeyForm` |
| `set_password` | `addons.authentication.forms.SetPasswordForm` |

`SignupForm` adds `first_name` and `last_name` fields and enforces strong password validation.

---

## OAuth Providers

### Google and GitHub

Both providers are registered in `SOCIALACCOUNT_PROVIDERS` in `server/settings.py`.

**Required environment variables:**
```
SOCIAL_AUTH_CLIENT_ID_GOOGLE
SOCIAL_AUTH_CLIENT_SECRET_GOOGLE
SOCIAL_AUTH_CLIENT_ID_GITHUB
SOCIAL_AUTH_CLIENT_SECRET_GITHUB
```

**Avatar sync on OAuth login** (`addons/authentication/signals.py`):

When a user links a social account (`SocialAccount.post_save(created=True)`), the `on_social_linked` signal:
1. Extracts the avatar URL from `extra_data`:
   - Google: `extra_data["picture"]`
   - GitHub: `extra_data["avatar_url"]`
2. Saves it to `profile.avatar_url` and sets `profile.avatar_source` to the provider name
3. Only sets if no provider URL is already stored (`profile.avatar_url` is empty)

When a social account is removed (`SocialAccount.post_delete`), the `on_social_unlinked` signal clears or refreshes the avatar URL from any remaining linked accounts.

### Adding a New OAuth Provider

1. Install the allauth provider package (or use a built-in one)
2. Add to `INSTALLED_APPS` (third-party section in settings)
3. Add to `SOCIALACCOUNT_PROVIDERS` dict in settings
4. Add avatar URL extraction in `authentication/signals.py` → `_extract_provider_avatar()`

---

## JWT API Authentication

**Default DRF settings:**
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}
```

**Endpoints:**
- `POST /api/token/` — obtain access + refresh token pair
- `POST /api/token/refresh/` — exchange refresh token for new access token

**Usage** (for microservices or JS clients):
```javascript
const resp = await fetch("/api/token/", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username: "...", password: "..."})
});
const {access, refresh} = await resp.json();
// Use access token in subsequent requests:
// Authorization: Bearer <access>
```

HTML views use session authentication, not JWT — JWT is for API-to-API and JS-to-API calls.

---

## Allauth URLs vs Custom Authentication URLs

**Allauth URLs** (at `/accounts/`, registered in `server/urls.py`):
- `/accounts/login/` — login page
- `/accounts/signup/` — registration
- `/accounts/logout/` — logout (allauth handles this)
- `/accounts/email/` — email management
- `/accounts/social/connections/` — manage social accounts
- `/accounts/password/change/` — allauth password change
- `/accounts/confirm-email/<key>/` — email confirmation

**Custom authentication addon URLs** (registered at root level):
- `/logout/` — custom logout view (shows a message)
- `/account/delete/` — delete account modal
- `/accounts/password/set/modal/` — set password modal (for users without a password)
- `/accounts/password/change/modal/` — change password modal
- `/accounts/password/reset/modal/` — reset password modal
- `/account/connections/remove/<pk>/` — confirm social account removal modal
- `/account/connections/remove/<pk>/do/` — actual removal (POST)

Note: The modal password routes shadow the allauth default password routes — users are directed to modals rather than full-page allauth forms.

---

## Superuser Bootstrap

On every `post_migrate` for the `authentication` app, `create_admin_role` runs and calls `_ensure_base_superuser()`.

If all three env vars are set, it will:
1. **Create** the superuser (if `username` not found) with `create_superuser()`
2. **Update** an existing user with the same username: ensures `is_superuser=True`, `is_staff=True`, correct Role
3. **Ensure** an allauth `EmailAddress` row exists for the superuser, marked as primary and verified

```
DJANGO_SUPERUSER_USERNAME  (or SUPERUSER_USERNAME)
DJANGO_SUPERUSER_EMAIL     (or SUPERUSER_EMAIL)
DJANGO_SUPERUSER_PASSWORD  (or SUPERUSER_PASSWORD)
```

This is idempotent — safe to run on every deploy. Password is only set on creation, not on subsequent runs.

---

## Password Validation

Custom strength validation in `addons/authentication/forms.py`:

`validate_password_strength(value)` checks:
- At least 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character (`!@#$%^&*()_+-=[]{}|;':\",./<>?`)

Called in `SignupForm.clean_password1()`. Modal password forms (change/set/reset) use allauth's built-in validators (configured via `AUTH_PASSWORD_VALIDATORS` in settings), not this custom one.
