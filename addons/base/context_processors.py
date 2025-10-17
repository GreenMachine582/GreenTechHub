
def default_context(request):
    return {
        'site_name': "GreenTechHub",
        'meta_description': "Serves to showcase innovative projects, exploring a curated library of games, and accessing embedded services that enhance user experiences.",
        'meta_keywords': "GreenTechHub, showcase, games library, django, microservices",
        'site_path': request.path
    }
