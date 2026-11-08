"""
`core` — Neyora's own client-onboarding and cross-cutting infrastructure.

This is the Neyora-side counterpart to UrbanNest's `neyora_interface_layer` app
(see calendar-scheduling/UrbanNest_InterfaceLayer_Scoping.md in the project docs —
that one lives inside UrbanNest-Core-Backend, this one lives here).

Scoped for Phase 0.5 of the architecture doc (calendar-scheduling/
UrbanNest_CalendarScheduling_Architecture.md, §2.7/§2.8/§20). Not built yet —
this file is a placeholder marking where the work lands, not real models.

What belongs here, when it's built:
  - NeyoClient            — one row per PM System that integrates with Neyora
                            (client_id, the long-lived API key, onboarding status).
                            §2.7 "client onboarding".
  - NeyoReferenceValue    — the Neyora-side half of the CoreNeyoraFieldMapping sync
                            (§2.6) — may end up here or in `notifications`, which
                            also touches it; not yet decided.
  - The sandbox-client flow (ARCH_056).
  - The widget-token model/table backing POST /api/widget-tokens/ (§20.2) — the
    actual short-lived token issuance Neyora's own API exposes, which UrbanNest's
    neyora_interface_layer.client.NeyoraClient.mint_widget_token() calls into.

Do not add real models here without re-reading §2.7/§2.8/§20 first — this app is the
security boundary between "a PM System's long-lived API key" and "a browser-facing
short-lived widget token," and getting that boundary wrong is the one mistake this
whole initiative is designed to prevent (see the architecture doc's own framing).
"""
