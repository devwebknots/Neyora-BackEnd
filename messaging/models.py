"""
`messaging` — the Conversation/Messaging module (Phase 1B of the architecture doc).

Scoped for Phase 1B of calendar-scheduling/UrbanNest_CalendarScheduling_Architecture.md.
Not built yet — this file is a placeholder marking where the work lands, not real
models. Built alongside the Messages screen's FE, same as `notifications` (Phase
1A) — see that app's models.py docstring for the shared build-order context.

What belongs here, when it's built:
  - NeyoConversation      — can be linked to a Lead stub (ARCH_046) once that
                            provisional model exists (see `leads`-equivalent work,
                            architecture doc §8.1) — the Lead model itself is NOT
                            built in this app; only the FK/relationship lives here.
  - NeyoMessage           — its own independent read state, separate from
                            NeyoNotification's read state (see `notifications`
                            app's docstring, §5.2's distinction between "pointing
                            at a NeyoConversation" and the message itself).

Feeds the NEW_MESSAGE notification trigger in `notifications` once both exist.
"""
