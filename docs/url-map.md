# URL Map

## How URLs Are Registered

`server/urls.py` auto-discovers URL patterns using a scandir loop:

```python
urlpatterns = [
    path('', include(f"addons.{app.name}.urls"))
    for app in scandir(settings.ADDONS_DIR)
    if app.is_dir() and (settings.ADDONS_DIR / app.name / "urls.py").exists()
]
urlpatterns += [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
]
```

**Key implications:**
- Each addon's `urls.py` is included **at the root path** (no prefix applied by `server/urls.py`)
- Each addon is responsible for its own path prefixes
- Addon URL files are auto-discovered — no manual registration needed
- The Django admin is at `/admin/` and allauth is at `/accounts/`
- `MEDIA_URL` (`/media/`) is added in DEBUG mode only (via `static()` helper in `urls.py`)

---

## base Addon

**File:** `addons/base/urls.py`

| Pattern | Name | View | Notes |
|---|---|---|---|
| `/` | `root-redirect` | `RedirectView` | Permanent=False; redirects to `home` |
| `/home/` | `home` | `base.views.home` | Renders `index.html` |
| `/users/profile/` | `users-profile` | `base.views.user_profile` | GET: profile page; POST: update avatar |
| `/me/avatar/` | `serve-my-avatar` | `base.views.serve_my_avatar` | Serves private avatar file; login required; sets cache headers |

---

## authentication Addon

**File:** `addons/authentication/urls.py`

| Pattern | Name | View | Notes |
|---|---|---|---|
| `/authentication/` | — | `django.contrib.auth.urls` | Django's built-in auth URLs (login, logout, password, etc.) |
| `/logout/` | `logout` | `views.user_logout` | Custom logout; shows "You have been logged out." message |
| `/account/delete/` | `users-delete-account` | `DeleteAccountModalView` | Modal; requires typing "DELETE" to confirm; blocks superuser deletion |
| `/accounts/password/set/modal/` | `password-set-modal` | `SetPasswordModalView` | Modal; for users who signed up via OAuth (no password set) |
| `/accounts/password/change/modal/` | `password-change-modal` | `ChangePasswordModalView` | Modal; for changing existing password |
| `/accounts/password/reset/modal/` | `password-reset-modal` | `ResetPasswordModalView` | Modal; sends password reset email |
| `/account/connections/remove/<int:pk>/` | `users-delete-connection-confirm` | `RemoveConnectionConfirmView` | AJAX GET: renders confirm modal |
| `/account/connections/remove/<int:pk>/do/` | `users-remove-connection` | `views.remove_connection` | POST: removes social account; prevents lockout (can't remove if no password) |
| `/api/token/` | `token_obtain_pair` | `TokenObtainPairView` | JWT; POST with `{username, password}`; returns `{access, refresh}` |
| `/api/token/refresh/` | `token_refresh` | `TokenRefreshView` | JWT; POST with `{refresh}`; returns `{access}` |
| `/api/userinfo/` | `userinfo` | `views.user_info` | POST; JWT auth; returns `{id, username, email, first_name, last_name}` |
| `/api/access-check/` | `access_check` | `views.access_check` | POST; JWT auth; body `{group: "code_name"}`; returns `{allowed: bool}` |

---

## microservice Addon

**File:** `addons/microservice/urls.py`

| Pattern | Name | View | Notes |
|---|---|---|---|
| `/api/<str:service>/<path:path>` | `microservice-proxy` | `MicroserviceProxyView` | DRF APIView; JWT auth; forwards request to registered microservice with matching prefix |

---

## pyfinbot Addon

**File:** `addons/pyfinbot/urls.py`

### Stock Management

| Pattern | Name | View | Notes |
|---|---|---|---|
| `/pyfinbot/stock/list/` | `pyfinbot-stock-list` | `StockListView` | Tabulator table; data fetched via `/api/pyfinbot/stocks/` proxy |
| `/pyfinbot/stock/form/` | `pyfinbot-stock-form` | `StockFormView` | Create mode (no `record_id`) |
| `/pyfinbot/stock/form/<int:record_id>/` | `pyfinbot-stock-form` | `StockFormView` | Update mode; prefills from microservice GET |
| `/pyfinbot/stock/delete/<int:record_id>/` | `pyfinbot-stock-delete` | `StockDeleteView` | AJAX modal confirm + DELETE to microservice |
| `/pyfinbot/stocks/sync/<str:market>/` | `pyfinbot-market-sync-action` | `SyncMarketStocksView` | POST action; syncs stocks for given market string |

### Transaction Management

| Pattern | Name | View | Notes |
|---|---|---|---|
| `/pyfinbot/transaction/list/` | `pyfinbot-transaction-list` | `TransactionListView` | Tabulator table |
| `/pyfinbot/transaction/form/` | `pyfinbot-transaction-form` | `TransactionFormView` | Create mode |
| `/pyfinbot/transaction/form/<int:record_id>/` | `pyfinbot-transaction-form` | `TransactionFormView` | Update mode; uses `transform_initial` to flatten nested `stock` object |
| `/pyfinbot/transaction/delete/<int:record_id>/` | `pyfinbot-transaction-delete` | `TransactionDeleteView` | AJAX modal confirm + DELETE |

---

## allauth URLs

**Registered at:** `path('accounts/', include('allauth.urls'))`

Common patterns under `/accounts/`:

| Pattern | Description |
|---|---|
| `/accounts/login/` | Login page (email or username) |
| `/accounts/signup/` | Registration (uses custom `SignupForm`) |
| `/accounts/logout/` | Allauth logout (prefer `/logout/` for custom message) |
| `/accounts/email/` | Email address management |
| `/accounts/confirm-email/<key>/` | Email confirmation link |
| `/accounts/password/change/` | Full-page password change (prefer modal at `/accounts/password/change/modal/`) |
| `/accounts/password/reset/` | Full-page password reset |
| `/accounts/password/reset/key/<uid>/<key>/` | Password reset from email link |
| `/accounts/social/connections/` | Manage connected social accounts |
| `/accounts/google/login/` | Initiate Google OAuth |
| `/accounts/github/login/` | Initiate GitHub OAuth |
| `/accounts/google/login/callback/` | Google OAuth callback |
| `/accounts/github/login/callback/` | GitHub OAuth callback |

---

## Django Admin

**URL:** `/admin/`

**Registered models:**

| Model | Admin class | Notes |
|---|---|---|
| `authentication.User` | Registered | Custom user model |
| `authentication.Role` | Registered | |
| `authentication.GroupProfile` | Registered | |
| `microservice.Microservice` | Registered | Manage service registry here |
| `auth.Group` | Default Django admin | |
| `auth.Permission` | Default Django admin | |
| `sites.Site` | Default Django admin | Domain/name auto-set by signal |
| `socialaccount.SocialApp` | Allauth admin | Register OAuth apps here too (allauth can use DB or settings) |
| `socialaccount.SocialAccount` | Allauth admin | User-linked social accounts |

---

## URL Name Reference (Alphabetical)

Use these names with `reverse("name")` or `{% url "name" %}`:

| URL Name | Pattern | Notes |
|---|---|---|
| `access_check` | `/api/access-check/` | POST; JWT auth |
| `home` | `/home/` | |
| `logout` | `/logout/` | |
| `microservice-proxy` | `/api/<service>/<path>` | JWT auth |
| `password-change-modal` | `/accounts/password/change/modal/` | AJAX only |
| `password-reset-modal` | `/accounts/password/reset/modal/` | AJAX only |
| `password-set-modal` | `/accounts/password/set/modal/` | AJAX only |
| `pyfinbot-market-sync-action` | `/pyfinbot/stocks/sync/<market>/` | POST |
| `pyfinbot-stock-delete` | `/pyfinbot/stock/delete/<record_id>/` | AJAX |
| `pyfinbot-stock-form` | `/pyfinbot/stock/form/` or `/pyfinbot/stock/form/<record_id>/` | |
| `pyfinbot-stock-list` | `/pyfinbot/stock/list/` | |
| `pyfinbot-transaction-delete` | `/pyfinbot/transaction/delete/<record_id>/` | AJAX |
| `pyfinbot-transaction-form` | `/pyfinbot/transaction/form/` or `/pyfinbot/transaction/form/<record_id>/` | |
| `pyfinbot-transaction-list` | `/pyfinbot/transaction/list/` | |
| `root-redirect` | `/` | |
| `serve-my-avatar` | `/me/avatar/` | Login required |
| `token_obtain_pair` | `/api/token/` | simplejwt |
| `token_refresh` | `/api/token/refresh/` | simplejwt |
| `userinfo` | `/api/userinfo/` | POST; JWT auth |
| `users-delete-account` | `/account/delete/` | AJAX modal |
| `users-delete-connection-confirm` | `/account/connections/remove/<pk>/` | AJAX modal GET |
| `users-profile` | `/users/profile/` | |
| `users-remove-connection` | `/account/connections/remove/<pk>/do/` | POST |

---

## Private Media Note

**There is no direct URL for uploaded avatars.**

The `Profile.avatar` field uses `private_storage` (a `FileSystemStorage` with `base_url=None`). Calling `profile.avatar.url` raises `ValueError`.

The only way to serve an avatar is through:
- `/me/avatar/` (`serve-my-avatar`) — serves the currently authenticated user's avatar with auth enforcement and cache headers
- `profile.effective_avatar_url` — returns the `/me/avatar/` URL if an upload exists, or the OAuth provider URL, or `None`

Public media files (non-avatar uploads, if any) are served at `/media/` in DEBUG mode only. In production, they are served from the `media/` bind mount directory and would need a separate web server or CDN — this is not currently configured.
