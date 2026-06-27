# Data Models

## Entity Relationship Diagram

```
django.contrib.auth.Group
  │  OneToOne (related_name: profile)
  ▼
GroupProfile  (addons.authentication)
  │
  └─── code_name: slugified group name

Role  (addons.authentication)
  │  M2M → Group
  │  M2M → Permission
  │
  FK (nullable, SET_NULL, related_name: users)
  │
User  (addons.authentication)  ← AUTH_USER_MODEL
  │  OneToOne (related_name: profile, CASCADE)
  ▼
Profile  (addons.base)

Microservice  (addons.microservice)  ← standalone, no FK relationships
```

---

## authentication.User

**File:** `addons/authentication/models.py`

Extends `django.contrib.auth.models.AbstractUser`. This is `AUTH_USER_MODEL`. Always import via `get_user_model()` or use `settings.AUTH_USER_MODEL` in ForeignKey definitions.

**Additional fields:**

| Field | Type | Default | Notes |
|---|---|---|---|
| `role` | FK → Role | `null=True, blank=True` | `on_delete=SET_NULL`; `related_name="users"` |

All `AbstractUser` fields are inherited: `username`, `email`, `first_name`, `last_name`, `is_staff`, `is_superuser`, `is_active`, `date_joined`, `last_login`, `password`, `groups` (M2M), `user_permissions` (M2M).

**Methods:**

```python
def hasGroups(self, code_name: str, *code_names: str) -> bool
```
Returns `True` if the user belongs to ANY of the named groups (by `GroupProfile.code_name`).

Checks two sources:
1. `user.groups` — direct Django group membership
2. `user.role.groups` — groups inherited via the user's Role (if a Role is set)

OR logic across all provided `code_names`. Example:
```python
user.hasGroups("admin_group")                 # single check
user.hasGroups("admin_group", "api_group")    # True if user has either
```

---

## authentication.Role

**File:** `addons/authentication/models.py`

A named bundle of Groups and Permissions. One Role can span many Groups. Users inherit all Groups associated with their Role.

**Fields:**

| Field | Type | Notes |
|---|---|---|
| `name` | CharField(50, unique) | Human-readable name; "Admin" is special (auto-created) |
| `description` | TextField | Optional description |
| `permissions` | M2M → Permission | Direct Django permissions |
| `groups` | M2M → Group | All groups this role grants |

**The Admin role** is special:
- Auto-created on `post_migrate` by `authentication.signals.create_admin_role`
- Always contains **all** Groups in the system (re-synced on each migrate)
- Automatically assigned to all superusers
- Every new Group is automatically added to Admin role via `add_new_group_to_admin_role` signal

---

## authentication.GroupProfile

**File:** `addons/authentication/models.py`

Extends Django's built-in `Group` model with a stable slug identifier and description.

**Fields:**

| Field | Type | Notes |
|---|---|---|
| `group` | OneToOne → Group | `on_delete=CASCADE`; `related_name="profile"` |
| `description` | TextField | Optional description |
| `code_name` | CharField(50, unique) | Auto-generated: `group.name.lower().replace(' ', '_')` |

**Access:** `group.profile` returns the GroupProfile. `group.profile.code_name` is the stable identifier.

**Static methods:**

```python
GroupProfile.get_group_by_code_name(code_name: str) -> Group | None
```
Returns the Django `Group` object for the given code_name, or `None`.

```python
GroupProfile.createGroupAndProfile(group_name: str, description: str) -> GroupProfile
```
Preferred factory — creates the Group AND GroupProfile together idempotently (`get_or_create`). Use this instead of bare `Group.objects.create()` to ensure the GroupProfile exists.

**Auto-creation:** A `GroupProfile` is created automatically whenever a `Group` is created, via `authentication.signals.create_group_profile`.

---

## base.Profile

**File:** `addons/base/models.py`

Stores user-specific display preferences, primarily avatar management.

**Fields:**

| Field | Type | Notes |
|---|---|---|
| `user` | OneToOne → User | `on_delete=CASCADE`; `related_name="profile"` |
| `avatar` | ImageField | Private storage (`private_storage`); path: `avatars/u{id}/{uuid}{ext}` |
| `avatar_url` | URLField | Provider-supplied URL (from Google/GitHub OAuth) |
| `avatar_source` | CharField(16) | Choices: `"upload"`, `"google"`, `"github"`, `"none"` |

**`avatar` field details:**
- Uses `private_storage` (a `FileSystemStorage` at `PRIVATE_MEDIA_ROOT` with `base_url=None`)
- **`profile.avatar.url` raises `ValueError`** — private storage has no URL
- Access only via the `/me/avatar/` view (which enforces authentication)
- Allowed extensions: jpg, jpeg, png, webp

**Cached properties:**

```python
@cached_property
def has_upload(self) -> bool
```
`True` if `self.avatar` is set (file field is non-empty).

```python
@cached_property
def effective_avatar_url(self) -> str | None
```
The safe URL to use in `<img src="...">`. Priority:
1. `/me/avatar/?v={mtime}` — if a file upload exists (cache-busted by file mtime)
2. `self.avatar_url` — if a provider URL is stored
3. `None` — no avatar

**Auto-creation:** A Profile is created for every new User via `base.signals.createProfile`.

---

## microservice.Microservice

**File:** `addons/microservice/models.py`

Registry of external microservices. Managed via Django admin. `MicroserviceClient` does a live DB lookup by prefix at request time.

**Fields:**

| Field | Type | Notes |
|---|---|---|
| `name` | CharField(100, unique) | Human-readable name |
| `description` | TextField | Optional |
| `prefix` | CharField(50, unique) | Stable identifier used in code (e.g., `"pyfinbot"`) |
| `base_url` | CharField(200) | Base URL of the service (e.g., `http://pyfinbot:8001/`) |
| `version` | CharField(20) | Default: `"1.0"` |
| `is_active` | BooleanField | Default: `True`; inactive services are ignored |
| `registered_at` | DateTimeField | Auto-set on creation |

**Ordering:** `Meta.ordering = ["name"]`

**Custom manager:** `objects = MicroserviceManager.from_queryset(MicroserviceQuerySet)()`
- `Microservice.objects.active()` — filters `is_active=True`
- `Microservice.objects.getByPrefix(prefix)` — returns active service by prefix or `None`

**Static method:**
```python
Microservice.getService(prefix: str) -> Microservice | None
```
Returns active Microservice or `None` (logs exception on miss).

**Instance method:**
```python
def buildUrl(self, path: str) -> str
```
Constructs the full request URL:
```python
urljoin(base_url.rstrip('/'), '/api/' + path.lstrip('/'))
# e.g. buildUrl("/stocks/") → "http://pyfinbot:8001/api/stocks/"
```
Note: `/api/` is always inserted between `base_url` and `path`.

---

## Signals Summary

All signals across `addons/authentication/signals.py` and `addons/base/signals.py`:

| Signal | Sender | Trigger | Effect |
|---|---|---|---|
| `base.createProfile` | User | `post_save(created=True)` | Creates a `Profile` for the new user |
| `base.delete_old_avatar_on_change` | Profile | `pre_save` | Deletes old avatar file from private storage when replaced |
| `base.delete_avatar_on_delete` | Profile | `post_delete` | Deletes avatar file when Profile is deleted |
| `base.configure_site_after_migrate` | any app | `post_migrate` | Updates `django.contrib.sites.Site` row from `SITE_DOMAIN`/`SITE_NAME` |
| `authentication.create_group_profile` | Group | `post_save(created=True)` | Creates a `GroupProfile` for the new Group |
| `authentication.create_admin_role` | authentication app | `post_migrate` | Creates/updates "Admin" Role; re-syncs all Groups into it; ensures superusers have it; runs `_ensure_base_superuser()` |
| `authentication.assign_admin_role_to_superuser` | User | `post_save(created=True, is_superuser=True)` | Assigns "Admin" Role to newly created superusers |
| `authentication.add_new_group_to_admin_role` | Group | `post_save(created=True)` | Adds every new Group to the "Admin" Role |
| `authentication.on_social_linked` | SocialAccount | `post_save(created=True)` | Extracts avatar URL from Google/GitHub extra_data; saves to Profile if no existing URL |
| `authentication.on_social_unlinked` | SocialAccount | `post_delete` | Clears or refreshes avatar URL/source when a social account is removed |

**Signal connection:** All signals are connected by importing the signals module in the relevant `AppConfig.ready()`. `base.apps.AppConfig.ready()` imports `from . import signals`. `authentication.apps.AppConfig.ready()` does the same.
