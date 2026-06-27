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

    def _group_ids(self) -> frozenset[int]:
        """All effective group IDs for this user (direct + role-inherited)."""
        ids = set(self.groups.values_list('id', flat=True))
        if self.role_id:
            ids |= set(self.role.groups.values_list('id', flat=True))
        return frozenset(ids)

    def hasGroups(self, *args) -> bool:
        """Check group membership with optional boolean expressions.

        Forms:
          hasGroups("a", "b")              — OR across strings (backward compatible)
          hasGroups(G("a") & G("b"))       — GroupExpr with &, |, ~ operators
          hasGroups({"combinator": ...})   — querybuilder-compatible dict tree
        """
        from .access import GroupExpr, eval_group_tree
        group_ids = self._group_ids()

        if len(args) == 1 and isinstance(args[0], GroupExpr):
            return args[0].eval(group_ids)

        if len(args) == 1 and isinstance(args[0], dict):
            return eval_group_tree(args[0], group_ids)

        for code_name in args:
            group = GroupProfile.get_group_by_code_name(str(code_name))
            if group and group.id in group_ids:
                return True
        return False
