"""
`scheduling` — the Calendar module (Phase 1C of the architecture doc).

Named `scheduling`, not `calendar` — Python's own standard library already has a
`calendar` module, and naming a Django app the same thing risks `import calendar`
elsewhere in this project silently resolving to this app instead of the stdlib
module. "Scheduling" also matches the architecture doc's own title ("Calendar &
Scheduling") so nothing is lost by avoiding the collision.

Scoped for Phase 1C of calendar-scheduling/UrbanNest_CalendarScheduling_Architecture.md
(§5–§6). Not built yet — this file is a placeholder marking where the work lands,
not real models. The frontend's Calendar screen (Neyora-FrontEnd/src/Calendar/) is
already built against mocks shaped to match what these models will return — see
that repo's src/api/mockData.js for the exact field shapes to match.

What belongs here, when it's built:
  - NeyoCalendar          — PERSONAL (one per external_user_id, ARCH_043) or
                            TEAM/PROPERTY/ACCOUNT scoped (ARCH_061).
  - NeyoEventType         — category + scope (ARCH_058), per-client configurable.
  - NeyoCalendarEvent     — is_all_day/conferencing_url (ARCH_059), the generic
                            subject_title/subject_subtitle/subject_image_url/
                            subject_highlights/subject_actions display-enrichment
                            fields (ARCH_060), and .ics export support (ARCH_057).
  - NeyoEventParticipant  — accept/decline via Notification only, never a new
                            Conversation/Message model (ARCH_045).
"""
