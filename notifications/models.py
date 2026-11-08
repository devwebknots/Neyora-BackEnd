"""
`notifications` — the shared Notification foundation (Phase 1A of the architecture
doc), plus the reference-data model it depends on.

Scoped for Phase 1A of calendar-scheduling/UrbanNest_CalendarScheduling_Architecture.md
(§5). Not built yet — this file is a placeholder marking where the work lands, not
real models. Per the architecture doc's §16 build order, this is built alongside
the Messages screen's FE (it's what makes that screen's notification bell live —
see Neyora-FrontEnd/src/shared/TopBar.jsx, which already renders a mock unread
count waiting for this).

What belongs here, when it's built:
  - NeyoNotification      — ONE shared feed across every persona/module/client
                            integrating with Neyora (§5.1) — never a per-persona or
                            per-module notification table. Three categories only
                            (§5.2): informational, actionable-via-deep-link, and
                            pointing-at-a-NeyoConversation.
  - NeyoReferenceValue    — the Neyora-side table CoreNeyoraFieldMapping (on
                            UrbanNest's side, inside neyora_interface_layer) pushes
                            into via POST /api/core-reference-values/sync/ (see
                            calendar-scheduling/UrbanNest_InterfaceLayer_Scoping.md
                            §6). Upsert semantics (§15.2) — sync is idempotent.

Also wires the real SAVED_SEARCH_MATCH and FAVORITE_STATUS_CHANGE triggers into
UrbanNest's existing Marketplace saved-search/favorites code (via the Interface
Layer, MK_020) once this app's creation service exists, and NEW_MESSAGE once
`messaging`'s NeyoConversation exists.
"""
