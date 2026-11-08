"""
Stateless widget-token issuance — architecture doc §20.2.

The architecture doc's own wording ("e.g. a 15-60 minute JWT") describes the
*shape* of the credential — short-lived, signed, tamper-evident, carrying
only client_id + external_user_id — not a mandate to add a JWT library.
Neyora is both the only issuer and the only verifier of this token; nothing
outside this process ever needs to decode it per a public standard (no
third-party JWT consumer exists for this credential today), so Django's own
`django.core.signing` gives the identical security property (HMAC-signed
using SECRET_KEY, tamper-evident, expiry enforced on verify) for zero new
dependency. If a future requirement needs a standards-shaped JWT — e.g. a
client wants to verify the token itself without calling back to Neyora —
revisit then; don't add the dependency speculatively now.

No database row is created for a minted token (§20.2 point 3) — it's a pure
function of (client_id, external_user_id, Neyora's SECRET_KEY, wall clock).
"""

from django.core import signing

# A dedicated salt namespaces this signer from any other use of
# django.core.signing elsewhere in the project (there is none today, but
# this costs nothing and avoids a future collision).
WIDGET_TOKEN_SALT = "neyora.core.widget_token"

# §20.2: "a 15-60 minute JWT" — 60 minutes, the top of that range, so a
# widget mounted at the start of a long session doesn't re-mint mid-use any
# more often than necessary.
WIDGET_TOKEN_MAX_AGE_SECONDS = 60 * 60


class WidgetTokenError(Exception):
    """Raised by verify_widget_token() for any invalid, tampered, or expired token."""


def mint_widget_token(*, client_id: str, external_user_id: str) -> dict:
    """§20.2 steps 2-3. Returns {"token": ..., "expires_in": <seconds>}."""
    payload = {"client_id": client_id, "external_user_id": external_user_id}
    token = signing.dumps(payload, salt=WIDGET_TOKEN_SALT)
    return {"token": token, "expires_in": WIDGET_TOKEN_MAX_AGE_SECONDS}


def verify_widget_token(token: str) -> dict:
    """
    §20.2 step 6. Returns {"client_id": ..., "external_user_id": ...} on
    success. Raises WidgetTokenError on anything else — expired, tampered,
    or malformed — never returns a partial/best-effort payload.
    """
    try:
        payload = signing.loads(
            token,
            salt=WIDGET_TOKEN_SALT,
            max_age=WIDGET_TOKEN_MAX_AGE_SECONDS,
        )
    except signing.SignatureExpired as exc:
        raise WidgetTokenError("Widget token has expired.") from exc
    except signing.BadSignature as exc:
        raise WidgetTokenError("Widget token is invalid.") from exc

    if not isinstance(payload, dict) or "client_id" not in payload or "external_user_id" not in payload:
        raise WidgetTokenError("Widget token payload is malformed.")
    return payload
