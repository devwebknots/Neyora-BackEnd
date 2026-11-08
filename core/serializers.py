from rest_framework import serializers


class WidgetTokenRequestSerializer(serializers.Serializer):
    """Body of POST /api/widget-tokens/ — §20.2 step 2's exact shape:
    {"client_id": "UN", "external_user_id": "1057"}."""

    client_id = serializers.CharField(max_length=64)
    external_user_id = serializers.CharField(max_length=128)
