"""Personal cloud credentials are used only by local desktop requests."""

from contextvars import ContextVar
from urllib.parse import urlparse

cloud_permitted = ContextVar("rafinha_cloud_permitted", default=False)


def local_access(request):
    origin = request.headers.get("origin")
    return bool(
        request.client
        and request.client.host in {"127.0.0.1", "::1", "testclient"}
        and (not origin or urlparse(origin).hostname in {"127.0.0.1", "localhost", "::1"})
    )
