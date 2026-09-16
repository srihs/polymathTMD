from django.http import JsonResponse

HEALTHZ_PATH = "/healthz/"


class HealthCheckMiddleware:
    """Answer liveness probes before host checks, HTTPS redirects and sessions.

    Container and load-balancer probes hit the app over plain HTTP with whatever
    Host header they like, so this must sit first in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == HEALTHZ_PATH:
            return JsonResponse({"status": "ok"})
        return self.get_response(request)
