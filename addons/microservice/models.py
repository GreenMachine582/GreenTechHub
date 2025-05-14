from django.db import models

# Create your models here.
class Microservice(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    prefix = models.CharField(max_length=50, unique=True, help_text="URL path prefix like 'pyfinbot'")
    base_url = models.CharField(max_length=200, help_text="Base URL like http://pyfinbot:8001/")
    version = models.CharField(max_length=20, default="1.0")
    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (v{self.version})"
