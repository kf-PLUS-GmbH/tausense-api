from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, User

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser
