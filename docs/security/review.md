# Security Audit Findings

## Finding 1 — Django Admin is Enabled (Medium) -- resolved

## Finding 2 — Webhook Signature Verification is Optional (Medium)

**`plugins/github/webhooks.py:173-179`** — If no `webhook_secret` is configured, signature verification is skipped entirely (only a warning is logged). This means anyone who can reach the webhook URL can forge payloads to trigger build polling or steps repo scans.

The same pattern appears for push events at lines 260-264.

**Recommendation**: Reject webhooks when no secret is configured — return early instead of proceeding.

---

## Finding 3 — `StepsRepoRegisterView` Missing `LoginRequiredMixin` (Low-Medium)

**`core/views/ci_workflows.py:56`** — `class StepsRepoRegisterView(OperatorRequiredMixin, View)` uses only `OperatorRequiredMixin`. `OperatorRequiredMixin` does check `is_authenticated`, so it's functionally OK. But it's inconsistent with the pattern used everywhere else (e.g., `StepsRepoScanView` at line 173 also only has `OperatorRequiredMixin`). Not an active vulnerability, but inconsistency increases risk of future bugs.

---

## Finding 4 — WebSocket Consumers Lack Authorization Checks (Low-Medium)

**`core/consumers.py:28-30`** — `BasePollingConsumer.connect()` checks `user.is_authenticated` but does **not** verify that the user has access to the specific entity (service/repo). Any authenticated user can connect to `ws/services/<id>/` for any service ID and receive real-time state updates, regardless of project membership or role.

**Recommendation**: Add project-role checks in `connect()` similar to how the HTTP views use `ProjectViewerMixin`.

---

## Finding 5 — No Rate Limiting on API/Auth Endpoints (Low)

- **`core/views/api.py`** — The `step_validate_api` endpoint has no rate limiting. Token brute-forcing is possible.
- **`core/views/auth.py`** — The login view has no rate limiting or account lockout.
- **Webhook endpoints** — No rate limiting.

**Recommendation**: Consider `django-axes` or similar for login brute-force protection. Add rate limiting middleware or decorators for API endpoints.

---

## Things That Look Good

- **All HTTP views use `LoginRequiredMixin`** — every view class across `core/views/` and `plugins/` has either `LoginRequiredMixin` or a role mixin that checks authentication.
- **CSRF protection** is proper — only the API endpoint and webhook are `@csrf_exempt`, both for valid reasons (token auth and external webhooks).
- **CSP configuration** is solid — nonce-based scripts/styles, `frame-ancestors: none`, `object-src: none`.
- **Session security** — `HttpOnly`, `Secure` (in production), `SameSite` defaults.
- **HSTS** enabled in production, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`.
- **No raw SQL** anywhere in the codebase.
- **YAML parsing uses `safe_load`** (not `load`).
- **WebSocket origin validation** via `AllowedHostsOriginValidator` + `AuthMiddlewareStack`.
- **SECRET_KEY** is required from env var with no fallback.
- **Webhook uses `hmac.compare_digest`** for timing-safe comparison.
