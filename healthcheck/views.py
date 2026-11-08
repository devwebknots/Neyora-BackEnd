from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def healthcheck(request):
    """
    Unauthenticated liveness/readiness check: confirms the process is up AND can
    reach its own Postgres database (neyora_db) — not just that gunicorn is
    running. Intentionally outside the client-key auth boundary (§2.5/§13 of the
    architecture doc) since infra tooling (a load balancer, a deploy script) needs
    to call this with no credential at all.
    """
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_ok = False

    return Response(
        {
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "unreachable",
        },
        status=200 if db_ok else 503,
    )
