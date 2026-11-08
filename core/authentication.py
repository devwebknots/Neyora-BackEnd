"""
DRF authentication classes for Neyora's two-credential model (§2.8, §13's
API-surface table, §20.2).

Every Neyora endpoint accepts one of two credentials — never a Django user
session; Neyora has no concept of a logged-in human (§2.8: "End users never
authenticate with Neyora directly, ever"):

  - NeyoClientApiKeyAuthentication — the long-lived, server-to-server client
    API key ("Authorization: ApiKey <key>"). Full access to that one
    client_id. Required for POST /api/widget-tokens/ (§13: "Interface Layer
    only, long-lived key required... never callable with a short-lived
    token itself" — see core/views.WidgetTokenView, which deliberately
    wires only this class).
  - NeyoWidgetTokenAuthentication — the short-lived, per-client-per-user
    token minted by the above ("Authorization: Bearer <token>"). Scoped to
    exactly the client_id/external_user_id baked in at mint time.

Both set `request.user` to a small principal object (never Django's real
User model — Neyora has none) exposing `.is_authenticated = True` so the
project's default `IsAuthenticated` permission class works unmodified, plus
`.client_id` (and `.external_user_id`, None for the client-key principal)
that views read to scope every query — "every endpoint scopes to client_id
first, then the authenticated external_user_id within it" (§13).

Each `authenticate()` returns None (not raises) when its own header keyword
doesn't match, so DRF falls through to the next configured class — this is
what lets most endpoints accept either credential per §13 ("Neyora's auth
layer accepts either credential on its API") just by listing both in
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"], with no per-view branching.
"""

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from core.models import CLIENT_STATUS_ACTIVE, NeyoClient
from core.tokens import WidgetTokenError, verify_widget_token


class ClientPrincipal:
    """Authenticated via the long-lived client API key — full client scope,
    no single end user (server-to-server)."""

    is_authenticated = True

    def __init__(self, neyo_client: "NeyoClient"):
        self.neyo_client = neyo_client
        self.client_id = neyo_client.client_id
        self.external_user_id = None

    def __str__(self):
        return f"ClientPrincipal(client_id={self.client_id!r})"


class WidgetPrincipal:
    """Authenticated via a short-lived widget token — scoped to exactly one
    client_id + external_user_id, nothing more (§20.2 point 6)."""

    is_authenticated = True

    def __init__(self, client_id: str, external_user_id: str):
        self.neyo_client = None
        self.client_id = client_id
        self.external_user_id = external_user_id

    def __str__(self):
        return f"WidgetPrincipal(client_id={self.client_id!r}, external_user_id={self.external_user_id!r})"


class NeyoClientApiKeyAuthentication(BaseAuthentication):
    keyword = "ApiKey"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None  # not our scheme — let the next authentication class try

        try:
            neyo_client = NeyoClient.objects.select_related("status").get(api_key=parts[1])
        except NeyoClient.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid client API key.")

        if neyo_client.status.value_code != CLIENT_STATUS_ACTIVE:
            raise exceptions.AuthenticationFailed(
                f"Client {neyo_client.client_id!r} is not active (status={neyo_client.status.value_code!r})."
            )
        return (ClientPrincipal(neyo_client), None)

    def authenticate_header(self, request):
        return self.keyword


class NeyoWidgetTokenAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None  # not our scheme — let the next authentication class try

        try:
            payload = verify_widget_token(parts[1])
        except WidgetTokenError as exc:
            raise exceptions.AuthenticationFailed(str(exc))

        return (WidgetPrincipal(payload["client_id"], payload["external_user_id"]), None)

    def authenticate_header(self, request):
        return self.keyword
