"""
§13 API surface — the Interface-Layer-only, long-lived-key-only endpoint
that `core` owns (reference-data sync is the other one, not built yet):
widget-token minting (§20.2).
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import ClientPrincipal, NeyoClientApiKeyAuthentication
from core.serializers import WidgetTokenRequestSerializer
from core.tokens import mint_widget_token


class WidgetTokenView(APIView):
    """
    POST /api/widget-tokens/ — §20.2 steps 2-3.

    §13: "Interface Layer only, long-lived key required... never callable
    with a short-lived token itself." That "never" is enforced structurally,
    not by a runtime check: this view's own `authentication_classes` lists
    ONLY NeyoClientApiKeyAuthentication, not the project-wide default pair
    (core.authentication.NeyoWidgetTokenAuthentication is deliberately
    absent). A request presenting a widget token here authenticates as
    nothing and falls through to IsAuthenticated's plain 401.

    This endpoint never returns NEYORA_CLIENT_API_KEY itself, under any
    circumstance — see UrbanNest_InterfaceLayer_Scoping.md §5's own framing
    of this as "the one security property worth a named regression test."
    """

    authentication_classes = [NeyoClientApiKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WidgetTokenRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client_principal: ClientPrincipal = request.user
        requested_client_id = serializer.validated_data["client_id"]
        if requested_client_id != client_principal.client_id:
            return Response(
                {
                    "detail": (
                        f"client_id {requested_client_id!r} does not match the "
                        f"authenticated API key's client ({client_principal.client_id!r})."
                    )
                },
                status=403,
            )

        token_data = mint_widget_token(
            client_id=client_principal.client_id,
            external_user_id=serializer.validated_data["external_user_id"],
        )
        return Response(token_data, status=201)
