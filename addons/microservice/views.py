import logging

import requests
from urllib.parse import urljoin
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Microservice


_logger = logging.getLogger(__name__)

# Create your views here.

@method_decorator(csrf_exempt, name='dispatch')
class MicroserviceProxyView(View):
    def dispatch(self, request, *args, **kwargs):
        service_prefix = kwargs.get('service')
        path = kwargs.get('path', '')

        try:
            service = Microservice.objects.get(prefix=service_prefix, is_active=True)
        except Microservice.DoesNotExist:
            return JsonResponse({'error': f'Microservice "{service_prefix}" not found or inactive'}, status=404)

        # Compose full URL: base_url + remaining path
        target_url = urljoin(service.base_url.rstrip('/') + '/', path.lstrip('/'))

        _logger.debug(f"Forwarding request to {target_url}")

        headers = {k: v for k, v in request.headers.items() if k.lower() != 'host'}
        if request.method not in ["POST", "PUT", "PATCH"]:
            headers.pop('Content-Length', None)
            headers.pop('Content-Type', None)

        try:
            # Forward the request with original method, headers, params, and body
            response = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=request.GET,
                data=request.body if request.method in ["POST", "PUT", "PATCH"] else None,
                timeout=10
            )

            return HttpResponse(
                response.content,
                status=response.status_code,
                content_type=response.headers.get('Content-Type', 'application/json')
            )
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
