
def default_context(request):
    return {
        'app_name': 'GreenTechHub',
        'site_version': '1.0.0',
        'site_path': request.path
    }
