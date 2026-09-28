from django.contrib import admin

from core.roles import user_has_write_access, user_is_viewer


class TauSenseModelAdmin(admin.ModelAdmin):
    """Staff with group «TauSense Viewer» can browse but not change data."""

    def _write_allowed(self, request) -> bool:
        return user_has_write_access(request.user)

    def has_add_permission(self, request):
        return self._write_allowed(request) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return self._write_allowed(request) and super().has_change_permission(
            request,
            obj,
        )

    def has_delete_permission(self, request, obj=None):
        return self._write_allowed(request) and super().has_delete_permission(
            request,
            obj,
        )

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj is not None and user_is_viewer(request.user):
            return [
                f.name
                for f in self.model._meta.fields
                if f.name != 'id'
            ]
        return fields
