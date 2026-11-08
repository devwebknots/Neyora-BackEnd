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

Still a placeholder, not yet built:
  - NeyoClient            — one row per PM System that integrates with Neyora
                            (client_id, the long-lived API key, onboarding status).
                            §2.7 "client onboarding".
  - The sandbox-client flow (ARCH_056).
  - The widget-token model/table backing POST /api/widget-tokens/ (§20.2) — the
    actual short-lived token issuance Neyora's own API exposes, which UrbanNest's
    neyora_interface_layer.client.NeyoraClient.mint_widget_token() calls into.

Do not add NeyoClient/widget-token models here without re-reading §2.7/§2.8/§20
first — this app is the security boundary between "a PM System's long-lived API
key" and "a browser-facing short-lived widget token," and getting that boundary
wrong is the one mistake this whole initiative is designed to prevent (see the
architecture doc's own framing).
"""

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
