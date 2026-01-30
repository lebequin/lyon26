from django.contrib import admin

from .models import Visit, Tractage


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'date', 'knocked_doors', 'open_doors', 'open_rate', 'building_list')
    list_filter = ('date', 'buildings__voting_desk__district', 'buildings__voting_desk')
    filter_horizontal = ('buildings',)
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')

    def building_list(self, obj):
        buildings = obj.buildings.all()[:3]
        result = ", ".join(str(b) for b in buildings)
        if obj.buildings.count() > 3:
            result += f" (+{obj.buildings.count() - 3})"
        return result
    building_list.short_description = "Immeubles"

    def open_rate(self, obj):
        return f"{obj.open_rate}%"
    open_rate.short_description = "Taux d'ouverture"


@admin.register(Tractage)
class TractageAdmin(admin.ModelAdmin):
    list_display = ('label', 'type_tractage', 'voting_desk', 'nb_tractage', 'address')
    list_filter = ('type_tractage', 'voting_desk')
    search_fields = ('label', 'address')
    list_editable = ('nb_tractage',)
    ordering = ('-nb_tractage', 'label')
