"""
`core` — Neyora's own client-onboarding and cross-cutting infrastructure.

This is the Neyora-side counterpart to UrbanNest's `neyora_interface_layer` app
(see calendar-scheduling/UrbanNest_InterfaceLayer_Scoping.md in the project docs —
that one lives inside UrbanNest-Core-Backend, this one lives here).

Scoped for Phase 0.5 of the architecture doc (calendar-scheduling/
UrbanNest_CalendarScheduling_Architecture.md, §2.6/§2.7/§2.8/§20).

NeyoReferenceValue is now REAL (built ahead of the rest of Phase 0.5) — every
`scheduling` model's choice-shaped fields (ARCH_042: no hardcoded `choices=`
anywhere in Neyora) are FKs into it, so it had to exist before `scheduling`'s
real models could. Placed in `core` rather than `notifications` (previously
flagged here as undecided) because `scheduling`, `bookings`, and `messaging`
all need to FK into it too, and `core` is the one app every other app can
depend on without creating app-to-app coupling (`scheduling` importing from
`notifications`, etc.) — `core` is for exactly this: infrastructure with no
business meaning of its own.

NeyoClient is now REAL too (Phase 0.5, built for real rather than as a dev-only
auth stub — see the living plan doc's Step 1, revised after the user's explicit
"do everything in a logical order" decision). §2.7 Step 1's field table.

Still a placeholder, not yet built:
  - The sandbox-client flow (ARCH_056).
  - Widget-token issuance has NO model/table by design (§20.2 point 3: "No
    database row is created for this — it's a stateless, signed credential").
    See core/tokens.py for the mint/verify functions and core/authentication.py
    for the DRF authentication classes that consume them.

This app is the security boundary between "a PM System's long-lived API key"
(NeyoClient.api_key) and "a browser-facing short-lived widget token"
(core/tokens.py) — getting that boundary wrong is the one mistake this whole
initiative is designed to prevent (see the architecture doc's own framing).
Do not add a widget-token *model* here without re-reading §20.2 first — that
would contradict the "no database row" decision, not just duplicate it.
"""

import secrets

from django.core.exceptions import ValidationError
from django.db import models


class NeyoReferenceValue(models.Model):
    """
    Architecture doc §2.6 — Neyora's own reference-data table.

    The landing spot for whatever each PM System's own field-mapping table
    (`CoreNeyoraFieldMapping` on UrbanNest's side) pushes in via
    `POST /api/core-reference-values/sync/` (§13). Neyora never stores a
    human-readable label — that's entirely the calling PM System's concern,
    resolved by its own Interface Layer (§2.6).

    This is the FK target for every `choices=`-shaped field anywhere in
    Neyora (`ARCH_042`) — `calendar_type`, `status`, `access_level`, `scope`,
    `category`, `visibility`, `persona_context`, `role`, `response_status`,
    and so on. A plain Django `ForeignKey` can't itself constrain "only rows
    with this field_code" at the database level, so every FK to this model
    elsewhere in Neyora is paired with `validate_reference_value()` below,
    called from that model's own `clean()` — see scheduling/models.py for
    the pattern.
    """

    id = models.BigAutoField(primary_key=True)

    # Opaque scalar, not an IntegerField — per ARCH_044, Neyora never assumes
    # a particular native type for a client's own ids; the architecture doc's
    # worked example (§21.3) consistently represents client_id/external ids
    # as strings ("UN", "1057", "501", ...) even where the originating
    # system's real PK is an integer. Every opaque-scalar field in this
    # project (client_id, external_user_id, account_id, property, etc.)
    # follows this same convention: CharField, not IntegerField.
    client_id = models.CharField(max_length=64)

    field_code = models.CharField(max_length=64)
    value_code = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client_id", "field_code", "value_code"],
                name="uniq_neyorefvalue_client_field_value",
            )
        ]
        indexes = [
            models.Index(fields=["client_id", "field_code"]),
        ]

    def __str__(self):
        return f"{self.client_id}/{self.field_code}={self.value_code}"


def validate_reference_value(reference_value, *, field_code, client_id):
    """
    Shared guard for every FK-to-NeyoReferenceValue field in Neyora (ARCH_042).

    A plain ForeignKey only guarantees "this row exists somewhere in
    NeyoReferenceValue" — it says nothing about *which* field the row was
    meant for, or which client it belongs to. Without this check, nothing
    would stop a `NeyoCalendar.calendar_type` from silently pointing at a
    `NOTIFICATION_TYPE` row, or at another client's `CALENDAR_TYPE` row
    (which would be a client-isolation break, §2.5). Called from each
    model's own `clean()`; raises `django.core.exceptions.ValidationError`
    rather than returning a bool, so Django's normal `full_clean()`/admin/DRF
    validation flow surfaces it the same way as any other field error.

    `reference_value` may be None — callers are responsible for only invoking
    this when the field is actually required/populated; nullable reference
    fields (e.g. NeyoCalendarEvent.persona_context) should skip the call when
    the value is None rather than treating None as invalid.
    """
    if reference_value.field_code != field_code:
        raise ValidationError(
            f"Expected a NeyoReferenceValue with field_code={field_code!r}, "
            f"got field_code={reference_value.field_code!r} (id={reference_value.id})."
        )
    if reference_value.client_id != client_id:
        raise ValidationError(
            f"NeyoReferenceValue id={reference_value.id} belongs to client_id="
            f"{reference_value.client_id!r}, not {client_id!r} — cross-client "
            f"reference values are a client-isolation violation (§2.5)."
        )
    if not reference_value.is_active:
        raise ValidationError(
            f"NeyoReferenceValue id={reference_value.id} "
            f"({field_code}={reference_value.value_code}) is retired (is_active=False)."
        )


# field_code constants for NeyoClient's own two reference-scoped fields below.
# Self-referential by design: a NeyoClient's status/plan_tier are validated
# against NeyoReferenceValue rows scoped by that SAME client_id (e.g.
# client_id="UN" has its own CLIENT_STATUS="ACTIVE" row) — every client
# describes its own onboarding state the same way it describes everything
# else in Neyora (ARCH_042), including itself.
FIELD_CODE_CLIENT_STATUS = "CLIENT_STATUS"       # §2.7 Step 1 — ACTIVE/SUSPENDED
FIELD_CODE_CLIENT_PLAN_TIER = "CLIENT_PLAN_TIER"  # §2.7 Step 1 — entitlement tier, feature-gating only

# The two value_codes the architecture doc's own worked example (§21.3) uses
# for NeyoClient — not an exhaustive enum (ARCH_042: no hardcoded choices),
# just the well-known ones referenced directly from code (e.g. the API-key
# auth class below checking a client is ACTIVE before accepting its key).
CLIENT_STATUS_ACTIVE = "ACTIVE"
CLIENT_STATUS_SUSPENDED = "SUSPENDED"


def generate_client_api_key() -> str:
    """
    §2.7 Step 2 — "Neyora generates a client-scoped API key tied to that
    client_id." A random URL-safe token, not a JWT/signed structure like the
    widget token (core/tokens.py) — this credential is looked up by exact
    value against NeyoClient.api_key (see core/authentication.py), never
    decoded, so there's nothing for a signature to buy here. 43 chars from
    secrets.token_urlsafe(32) — plenty of entropy for a server-to-server-only
    secret that's never brute-forced over a public endpoint.
    """
    return secrets.token_urlsafe(32)


class NeyoClient(models.Model):
    """
    Architecture doc §2.7 Step 1 / §21.3's worked example.

    One row per PM System that integrates with Neyora — UrbanNest's own
    rollout is "Step 1 run for the first time," not a special case (§2.7's
    own framing); a future "Galaxy PMS" onboarding creates a second row here,
    nothing else.

    Deliberately excludes any billing/invoice detail (§2.7 Step 1) — that
    stays in each client's own system, never inside Neyora.
    """

    # Opaque scalar PK (ARCH_044) — "generated at registration," but for the
    # worked example (and UrbanNest's own real rollout) that's the short,
    # human-chosen "UN" the architecture doc itself uses throughout §21.3.
    # A future client ("Galaxy") gets its own short code the same way.
    client_id = models.CharField(max_length=64, primary_key=True)

    name = models.CharField(max_length=255)

    status = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="clients_by_status",
        limit_choices_to={"field_code": FIELD_CODE_CLIENT_STATUS},
    )
    plan_tier = models.ForeignKey(
        NeyoReferenceValue,
        on_delete=models.PROTECT,
        related_name="clients_by_plan_tier",
        limit_choices_to={"field_code": FIELD_CODE_CLIENT_PLAN_TIER},
    )

    # §2.7 Step 2 — the long-lived, server-to-server-only credential. Looked
    # up by exact match in core/authentication.py; never logged, never
    # returned from any API response (see core/views.WidgetTokenView's own
    # docstring on this point).
    api_key = models.CharField(max_length=128, unique=True, default=generate_client_api_key, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"NeyoClient(client_id={self.client_id!r}, name={self.name!r})"

    def clean(self):
        super().clean()
        if self.status_id:
            validate_reference_value(
                self.status, field_code=FIELD_CODE_CLIENT_STATUS, client_id=self.client_id
            )
        if self.plan_tier_id:
            validate_reference_value(
                self.plan_tier, field_code=FIELD_CODE_CLIENT_PLAN_TIER, client_id=self.client_id
            )
