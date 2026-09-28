from django.contrib import admin

from core.admin_mixins import TauSenseModelAdmin
from municipalities.models import Municipality


@admin.register(Municipality)
class MunicipalityAdmin(TauSenseModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
