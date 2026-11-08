"""
`bookings` — the Bookings module (Phase 1D of the architecture doc).

Scoped for Phase 1D of calendar-scheduling/UrbanNest_CalendarScheduling_Architecture.md.
Not built yet — this file is a placeholder marking where the work lands, not real
models. Per the architecture doc's §16 build order, the Bookings screen's FE is
built next (after Calendar), against mocks, before these models exist — see
ARCH_062.

What belongs here, when it's built:
  - NeyoBookingRequest        — no hardcoded choice fields anywhere (ARCH_042,
                                including .status — this was an explicit decision,
                                not an oversight: read §2.2's framing before adding
                                a plain CharField `choices=` here).
  - NeyoAvailabilityRule      — at LISTING scope, there is an open product question
                                (not an engineering one) on whether this reconciles
                                with ListingLeadSettings.showing_method/available_days
                                or stays independent — see
                                calendar-scheduling/UrbanNest_InterfaceLayer_Scoping.md
                                §4, and confirm with the user before building this,
                                don't guess.
  - NeyoAvailabilityException
  - NeyoSchedulingPolicy

A NeyoBookingRequest/NeyoEventBusinessLink's `listing` field is an opaque scalar
resolved through UrbanNest's neyora_interface_layer.resolvers — never assume it's
a bare Listing id; a grouped Multi-Unit member needs the two-tier fallback that
resolver implements (see that scoping doc's §4 and claude/UrbanNest_ActiveBacklog.md
process lesson 19 for why).
"""
