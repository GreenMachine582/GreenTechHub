from django.db import models
from django.contrib.auth.models import AbstractUser, Permission, Group


class GroupProfile(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='profile')
    description = models.TextField(blank=True)
    code_name = models.CharField(max_length=50, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code_name and self.group.name:
            self.code_name = self.group.name.lower().replace(' ', '_')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.group.name} ({self.code_name})"

    @staticmethod
    def get_group_by_code_name(code_name: str):
        try:
            return Group.objects.get(profile__code_name=code_name)
        except Group.DoesNotExist:
            return None

    @staticmethod
    def createGroupAndProfile(group_name: str, description: str):
        group, created = Group.objects.get_or_create(name=group_name)

        profile, _ = GroupProfile.objects.get_or_create(group=group)
        if created:
            profile.description = description
            profile.save()
        return profile


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    groups = models.ManyToManyField(Group, blank=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    def hasGroups(self, code_name: str, *code_names: tuple[str]) -> bool:
        user_group_ids = set(self.groups.values_list('id', flat=True))
        if self.role:
            user_group_ids |= set(self.role.groups.values_list('id', flat=True))

        code_names = (code_name,) + code_names
        for code_name in code_names:
            group = GroupProfile.get_group_by_code_name(code_name)
            if group and (group.id in user_group_ids):
                return True
        return False
