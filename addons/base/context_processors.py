
def default_context(request):
    return {
        'app_name': 'GreenTechHub',
        'user_authenticated': request.user.is_authenticated,
        'site_version': '1.0.0',
        'site_path': request.path
    }
