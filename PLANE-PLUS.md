# InfraWatch — Fork Change Manifest

Tracks all changes we've made on `main` vs upstream `master`.
Use this when merging upstream updates to know what to protect.

## Upstream Sync Workflow

```bash
# 1. Fetch latest upstream
git fetch origin master

# 2. Merge upstream into main
git checkout main
git merge origin/master

# 3. Resolve conflicts using this manifest — our changes take priority
#    Only 3 upstream files are modified (see below), rest are new files

# 4. Verify our additions still work
#    - plane.iw app is in INSTALLED_APPS
#    - plane.iw URLs are mounted
#    - estimate_patterns are included in API URLs
#    - build workflow exists
#    - deployments/infrawatch/ exists

# 5. Test, commit, push
```

## Change Categories

### 1. New Files (no conflict risk)

These are entirely ours — upstream will never touch them:

| File/Dir | Purpose |
|----------|---------|
| `.github/workflows/build-infrawatchlabs.yml` | Our Docker build/release pipeline (6 images) |
| `deployments/infrawatch/docker-compose.yml` | Our production docker-compose |
| `deployments/infrawatch/variables.env` | Our env template |
| `deployments/infrawatch/install.sh` | CLI installer (install/start/stop/upgrade/backup) |
| `apps/api/plane/iw/` | Our custom Django app (Pages & Estimates API v1 endpoints) |
| `INFRAWATCHLABS.md` | This file |

### 2. Modified Upstream Files (conflict risk on merge)

Only **3 files** — all are small 1-2 line additions:

#### `apps/api/plane/settings/common.py`
```python
# Added "plane.iw" to INSTALLED_APPS
INSTALLED_APPS = [
    ...
    "plane.api",
+   "plane.iw",       # <-- OUR LINE
    "plane.authentication",
    ...
]
```

#### `apps/api/plane/urls.py`
```python
# Added our iw URL mount
urlpatterns = [
    ...
    path("api/v1/", include("plane.api.urls")),
+   path("api/v1/", include("plane.iw.urls")),  # <-- OUR LINE
    ...
]
```

#### `apps/api/plane/api/urls/__init__.py`
```python
# Added estimate_patterns import and inclusion
+from .estimate import urlpatterns as estimate_patterns

urlpatterns = [
    ...
+   *estimate_patterns,  # <-- OUR LINE
    ...
]
```

### 3. Rebranded Files (from fix/version-stamp branch)

These replace `makeplane` references with `infrawatchlabs`:

| File | What changed |
|------|-------------|
| `apps/api/plane/license/management/commands/register_instance.py` | Version check API → our repo |
| `apps/admin/app/(all)/(dashboard)/sidebar-help-section.tsx` | "Report a bug" link |
| `apps/web/app/(all)/[workspaceSlug]/(projects)/star-us-link.tsx` | "Star us on GitHub" link |
| `apps/web/app/(all)/workspace-invitations/page.tsx` | "Star us on GitHub" link |
| `apps/web/core/components/power-k/config/help-commands.ts` | Cmd+K "Report bug" action |

### 4. Email Templates (TODO — not yet changed)

Still reference `makeplane` — low priority, cosmetic:
- `apps/api/templates/emails/invitations/project_invitation.html`
- `apps/api/templates/emails/user/user_activation.html`
- `apps/api/templates/emails/user/user_deactivation.html`
- `apps/api/templates/emails/user/email_updated.html`
- `apps/api/templates/emails/notifications/webhook-deactivate.html`
- `apps/api/templates/emails/notifications/issue-updates.html`
- `apps/api/plane/settings/openapi.py` (license URL)

## Quick Conflict Resolution Guide

On upstream merge, if conflicts appear in the 3 modified files:
1. Accept upstream changes
2. Re-add our lines (copy from section 2 above)
3. Done — our additions are independent of upstream logic
