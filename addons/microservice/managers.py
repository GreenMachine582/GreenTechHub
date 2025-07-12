
from django.db import models


class MicroserviceQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class MicroserviceManager(models.Manager):
    def get_by_prefix(self, prefix: str):
        return (
            self.get_queryset()
                .active()
                .get(prefix=prefix)
        )
