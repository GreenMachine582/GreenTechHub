
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site


def default_context(request):
    site_name, site_domain = '', ''
    try:
        current_site = get_current_site(request)
        site_name = getattr(current_site, "name", None)
        site_domain = getattr(current_site, "domain", None)
    except Exception:
        pass
    return {
        "site_name": site_name or settings.SITE_NAME,
        "site_domain": site_domain or settings.SITE_DOMAIN,
        'meta_description': "Serves to showcase innovative projects, exploring a curated library of games, and accessing embedded services that enhance user experiences.",
        'meta_keywords': "GreenTechHub, showcase, games library, django, microservices",
        'site_path': request.path
    }
