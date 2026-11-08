# Neyora — Backend

Neyora is a client-agnostic Notification / Conversation-Messaging / Calendar &
Scheduling engine. UrbanNest is its first customer, consuming it through a
dedicated **Interface Layer** that lives inside `UrbanNest-Core-Backend` (never
inside this repo — Neyora must stay fully client-agnostic, per `ARCH_049`).

Canonical architecture doc (frozen, Version 1): `UrbanNest_CalendarScheduling_Architecture.md`
in the UrbanNest project. Every decision referenced in this codebase's comments
(`ARCH_0xx`) is defined there.

## Current status

This is the Phase 0.5 scaffold only — a real, runnable Django project with no
Neyora-specific models yet. No `NeyoCalendar`/`NeyoNotification`/etc. exists
yet; those arrive in Phase 1A–1D per the architecture doc's §16 build order,
which this engagement is running **FE-first, screen by screen** (`ARCH_062`):
the Calendar screen's frontend is built first, against mocked responses shaped
to the already-frozen API contract (§13), and each screen's real backend phase
follows to replace the mocks — this repo's own build order follows that same
sequence.

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in SECRET_KEY, DB_* (see that file's own comments)
python manage.py migrate
python manage.py runserver 0.0.0.0:8002
```

Requires a reachable Postgres instance (see `.env.example`) — there is no
sqlite fallback. Per the architecture doc's own §17 testing strategy,
concurrency-sensitive behavior (the booking-conflict locking in §9.2) must be
tested against Postgres specifically; defaulting local dev to sqlite would let
that kind of bug hide until production.

`GET /api/health/` is unauthenticated and checks both process liveness and
database connectivity — use it for load-balancer/deploy-script health checks.

## ⚠️ The `.env` gotcha (read this before writing a management command or migration)

Every environment-derived value in this project goes through
`python-decouple`'s `config()` — **never** `os.environ`/`os.environ.get()`.
`python-decouple`'s own `.env` loader does not inject values into the real
process environment, so `os.environ.get(...)` silently sees nothing even when
`.env` has the value. This exact bug already shipped once, in
`UrbanNest-Core-Backend`'s own admin-seed migration, silently falling back to a
hardcoded default password in production (see
`infrastructure/UrbanNest_AWS_Deployment_Running.md` §7 Phase 3 step 6 in the
UrbanNest project). If you add a data migration or management command here
that reads a secret/config value (an admin seed password, an API key), import
`from decouple import config` and use that.

## Deployment

The shared EC2 instance (`urbannest-neyora-shared`) already has a `neyora` OS
user and an isolated `neyora_db`/`neyora_app` Postgres role provisioned and
idle, waiting for this repo to have a deployable project in it (now true) —
see `infrastructure/UrbanNest_AWS_Deployment_Running.md` §5/§7 Phase 5 in the
UrbanNest project for the exact deploy steps (a dedicated read-only deploy key
scoped to this repo only, systemd unit, Nginx `server_name`/proxy block,
certbot certificate — identical pattern to UrbanNest's own Phase 3 deploy,
just under the `neyora` OS user instead of `urbannest`).

## App layout

- `neyora_backend/` — project settings/urls/wsgi/asgi.
- `healthcheck/` — the one app that exists today; unauthenticated liveness
  check only.
- Future apps (not yet created, one per the architecture doc's model groups):
  a notifications app (`NeyoNotification`, Phase 1A), a conversations app
  (`NeyoConversation`/`NeyoMessage`, Phase 1B), a calendar app
  (`NeyoCalendar`/`NeyoCalendarEvent`/etc., Phase 1C), a scheduling app
  (`NeyoBookingRequest`/availability, Phase 1D), and a core/reference-data app
  (`NeyoClient`, `NeyoReferenceValue`, the widget-token endpoint — Phase 0.5).
  Exact app boundaries are a Phase 0.5 design decision, not fixed here.
